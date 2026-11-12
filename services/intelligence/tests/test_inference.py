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


async def test_timeout_and_invalid_output_have_bounded_local_fallback():
    local, cloud = (
        Provider(),
        Provider("groq", [InferenceFailure("invalid_output"), TimeoutError()]),
    )
    router = InferenceRouter(local, [cloud], cloud_content_allowed=True, attempts=2)
    await router.generate("Test", "Test", ResearchPlan, "verification", public_source_content=True)
    assert cloud.calls == 2 and local.calls == 1
    assert [item.status for item in router.usage] == ["invalid_output", "timeout", "ok"]


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


def test_credentials_are_masked_and_ollama_cannot_point_to_public_inference():
    settings = Settings(_env_file=None, groq_api_key_primary="test-secret")
    assert "test-secret" not in repr(settings)
    with pytest.raises(ValueError):
        Settings(_env_file=None, ollama_base_url="https://example.org")
