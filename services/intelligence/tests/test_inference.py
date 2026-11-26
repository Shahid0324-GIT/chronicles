import asyncio

import pytest

from src.application.inference import InferenceRouter
from src.application.research_contracts import (
    InferenceFailure,
    InferenceResult,
    InferenceUsage,
    ResearchPlan,
)
from src.infrastructure.config.settings import Settings


class Provider:
    def __init__(self, name="ollama", failures=()):
        self.name, self.model, self.credential = name, "test-model", name
        self.failures = list(failures)
        self.calls = 0

    async def available(self):
        return True

    async def generate(self, system, prompt, schema, task):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return InferenceResult(
            ResearchPlan(questions=["Synthetic question"]),
            InferenceUsage(self.name, self.model, self.credential, task, "ok", 1),
        )


@pytest.mark.parametrize(
    "mode,allowed,public,expected",
    [
        ("local", True, True, "ollama"),
        ("hybrid", False, True, "ollama"),
        ("cloud", True, False, "ollama"),
        ("hybrid", True, True, "groq"),
    ],
)
async def test_privacy_precedes_routing(mode, allowed, public, expected):
    local, cloud = Provider(), Provider("groq")
    router = InferenceRouter(local, [cloud], mode=mode, cloud_content_allowed=allowed)
    result = await router.generate(
        "Test", "Test", ResearchPlan, "verification", public_source_content=public
    )
    assert result.usage.provider == expected
    assert cloud.calls == (expected == "groq")


async def test_routine_hybrid_task_stays_local_and_missing_cloud_works():
    local, cloud = Provider(), Provider("groq")
    router = InferenceRouter(local, [cloud], cloud_content_allowed=True)
    await router.generate("Test", "Test", ResearchPlan, "extraction", public_source_content=True)
    assert not cloud.calls
    router = InferenceRouter(local, [], mode="cloud", cloud_content_allowed=True)
    assert (
        await router.generate(
            "Test", "Test", ResearchPlan, "verification", public_source_content=True
        )
    ).usage.provider == "ollama"


async def test_rate_limit_never_rotates_keys_and_cooldown_is_shared():
    local = Provider()
    primary = Provider("groq", [InferenceFailure("rate_limited", 120)])
    secondary = Provider("secondary")
    router = InferenceRouter(
        local, [primary, secondary], cloud_content_allowed=True, clock=lambda: 100
    )
    for _ in range(2):
        await router.generate(
            "Test", "Test", ResearchPlan, "verification", public_source_content=True
        )
    assert primary.calls == 1 and secondary.calls == 0 and local.calls == 2
    assert router.status()["cloud_cooldown"] is True


async def test_bounded_rate_limit_wait_retries_same_credential(monkeypatch):
    waits = []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", sleep)
    local = Provider()
    primary = Provider("groq", [InferenceFailure("rate_limited", 90)])
    secondary = Provider("secondary")
    router = InferenceRouter(
        local, [primary, secondary], cloud_content_allowed=True, cloud_rate_limit_wait_seconds=120
    )
    result = await router.generate(
        "Owned", "Owned", ResearchPlan, "verification", public_source_content=True
    )
    assert result.usage.provider == "groq"
    assert waits == [60, 30]
    assert primary.calls == 2 and secondary.calls == 0 and local.calls == 0


async def test_timeout_and_invalid_output_have_bounded_local_fallback():
    local, cloud = (
        Provider(),
        Provider("groq", [InferenceFailure("invalid_output"), TimeoutError()]),
    )
    router = InferenceRouter(local, [cloud], cloud_content_allowed=True, attempts=2)
    await router.generate("Test", "Test", ResearchPlan, "verification", public_source_content=True)
    assert cloud.calls == 2 and local.calls == 1
    assert [item.status for item in router.usage] == ["invalid_output", "timeout", "ok"]


async def test_presentation_fallback_preserves_final_review_budget_after_resume():
    local = Provider()
    cloud = Provider("groq", [InferenceFailure("invalid_output")])
    router = InferenceRouter(local, [cloud], cloud_content_allowed=True, max_calls=4)
    router.restore_budget([{"task": "presentation", "status": "ok", "model_call": True}])
    with pytest.raises(InferenceFailure, match="publication_review_budget_reserved"):
        await router.generate(
            "Owned",
            "Owned",
            ResearchPlan,
            "presentation",
            public_source_content=True,
            reserve_calls=2,
        )
    assert cloud.calls == 1 and local.calls == 0
    for _ in range(2):
        await router.generate("Owned", "Owned", ResearchPlan, "presentation_verification")
    assert router.total_used == 4 and local.calls == 2


async def test_router_serializes_local_inference():
    active, peak = 0, 0

    class Slow(Provider):
        async def generate(self, *args):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return await super().generate(*args)

    router = InferenceRouter(Slow(), [], concurrency=1)
    await asyncio.gather(
        *[router.generate("Test", "Test", ResearchPlan, "planning") for _ in range(3)]
    )
    assert peak == 1


async def test_waiting_cloud_request_rechecks_cooldown_after_acquiring_gate():
    local = Provider()

    class RateLimited(Provider):
        async def generate(self, *args):
            self.calls += 1
            await asyncio.sleep(0.01)
            raise InferenceFailure("rate_limited", 120)

    cloud = RateLimited("groq")
    router = InferenceRouter(local, [cloud], cloud_content_allowed=True)
    await asyncio.gather(
        *[
            router.generate(
                "Test", "Test", ResearchPlan, "verification", public_source_content=True
            )
            for _ in range(2)
        ]
    )
    assert cloud.calls == 1 and local.calls == 2


def test_credentials_are_masked_and_ollama_cannot_point_to_public_inference():
    settings = Settings(_env_file=None, groq_api_key_primary="test-secret")
    assert "test-secret" not in repr(settings)
    with pytest.raises(ValueError):
        Settings(_env_file=None, ollama_base_url="https://example.org")


def test_groq_response_format_is_configurable_without_changing_permissions():
    from src.infrastructure.inference import create_inference

    settings = Settings(
        _env_file=None,
        groq_api_key_primary="owned-test-key",
        groq_model="owned-test-model",
        groq_structured_output_method="json_schema",
        groq_structured_output_strict=True,
        ai_cloud_content_allowed=False,
    )
    router = create_inference(settings)
    assert router.cloud[0].method == "json_schema"
    assert router.cloud[0].strict
    assert not router.local.strict
    assert not router.cloud_content_allowed
    with pytest.raises(ValueError):
        Settings(_env_file=None, groq_structured_output_method="invented-format")


async def test_key_failover_is_opt_in_and_uses_the_second_account_before_local():
    for failover, expect_secondary in ((False, 0), (True, 1)):
        local = Provider()
        primary = Provider("groq", [InferenceFailure("rate_limited", 90)])
        secondary = Provider("secondary")
        router = InferenceRouter(
            local, [primary, secondary], cloud_content_allowed=True, key_failover=failover
        )
        result = await router.generate(
            "Owned", "Owned", ResearchPlan, "verification", public_source_content=True
        )
        assert secondary.calls == expect_secondary
        assert (result.usage.provider == "secondary") is bool(expect_secondary)
        assert local.calls == (0 if failover else 1)
        # The limited key stays cooling; the next call goes straight to the live key.
        again = await router.generate(
            "Owned", "Owned", ResearchPlan, "verification", public_source_content=True
        )
        assert primary.calls == 1
        assert (again.usage.provider == "secondary") is failover


async def test_quality_critical_calls_never_fall_back_to_the_local_model():
    local = Provider()
    cloud = Provider("groq", [InferenceFailure("rate_limited", 90)])
    router = InferenceRouter(local, [cloud], cloud_content_allowed=True)
    for expected in ("rate_limited", "cloud_unavailable"):
        with pytest.raises(InferenceFailure) as raised:
            await router.generate(
                "Owned",
                "Owned",
                ResearchPlan,
                "presentation",
                public_source_content=True,
                allow_local_fallback=False,
            )
        assert raised.value.code == expected and raised.value.retry_after > 0
    with pytest.raises(InferenceFailure, match="cloud_not_permitted"):
        await router.generate(
            "Owned", "Owned", ResearchPlan, "presentation", allow_local_fallback=False
        )
    assert local.calls == 0
