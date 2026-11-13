import asyncio
import json
from collections.abc import Callable
from dataclasses import replace
from time import monotonic

from pydantic import ValidationError

from src.application.ports.inference_cache import InferenceCache
from src.application.research_contracts import (
    InferenceFailure,
    InferenceProvider,
    InferenceResult,
    InferenceUsage,
    T,
    Task,
    validation_issues,
)
from src.domain.research import digest


class InferenceRouter:
    """Privacy policy precedes provider selection. No key rotation after rate limits."""

    def __init__(
        self,
        local: InferenceProvider,
        cloud: list[InferenceProvider],
        *,
        mode: str = "hybrid",
        cloud_content_allowed: bool = False,
        attempts: int = 2,
        timeout: float = 120,
        concurrency: int = 1,
        clock: Callable[[], float] = monotonic,
        cache: InferenceCache | None = None,
        max_calls: int = 1000,
        stage_limits: dict[str, int] | None = None,
    ) -> None:
        self.local, self.cloud = local, cloud
        self.mode, self.cloud_content_allowed = mode, cloud_content_allowed
        self.attempts, self.timeout, self.clock = attempts, timeout, clock
        self.gate = asyncio.Semaphore(concurrency)
        self.cloud_until = 0.0
        self.disabled: set[str] = set()
        self.usage: list[InferenceUsage] = []
        self.cache, self.max_calls, self.stage_limits = cache, max_calls, stage_limits or {}
        self.total_used = 0
        self.stage_used: dict[str, int] = {}

    def restore_budget(self, usage: list[dict[str, object]]) -> None:
        self.total_used = sum(
            bool(u.get("model_call", u.get("status") != "cache_hit")) for u in usage
        )
        self.stage_used = {}
        for u in usage:
            if u.get("model_call", u.get("status") != "cache_hit"):
                task = str(u.get("task"))
                self.stage_used[task] = self.stage_used.get(task, 0) + 1

    async def generate(
        self,
        system: str,
        prompt: str,
        schema: type[T],
        task: Task,
        *,
        public_source_content: bool = False,
    ) -> InferenceResult:
        async with self.gate:
            contract = schema.model_json_schema()
            if contract.get("type") != "object":
                raise InferenceFailure("schema_incompatible")
            eligible = self.mode != "local" and self.cloud_content_allowed and public_source_content
            prefer_cloud = eligible and (
                self.mode == "cloud" or task in {"verification", "identity_resolution"}
            )
            candidates = [self.local]
            last_code = "provider_unavailable"
            if prefer_cloud and self.clock() >= self.cloud_until:
                candidate = next((p for p in self.cloud if p.credential not in self.disabled), None)
                if candidate:
                    candidates.insert(0, candidate)
            for provider in candidates:
                repair_prompt = prompt
                for attempt in range(self.attempts):
                    start = self.clock()
                    attempted = False
                    try:
                        async with asyncio.timeout(self.timeout):
                            if not await provider.available():
                                raise InferenceFailure("model_unavailable")
                            revision = getattr(provider, "revision", None)
                            key = digest(
                                json.dumps(
                                    [
                                        "structured-v4",
                                        provider.name,
                                        provider.model,
                                        revision,
                                        system,
                                        prompt,
                                        contract,
                                        public_source_content,
                                    ],
                                    sort_keys=True,
                                )
                            )
                            cacheable = (
                                self.cache is not None
                                and bool(revision)
                                and task in {"extraction", "verification"}
                            )
                            if cacheable and self.cache:
                                saved = await self.cache.get(key)
                                if saved is not None:
                                    try:
                                        value = schema.model_validate(saved)
                                    except ValidationError:
                                        value = None
                                    if value is not None:
                                        usage = InferenceUsage(
                                            provider.name,
                                            provider.model,
                                            provider.credential,
                                            task,
                                            "cache_hit",
                                            0,
                                            model_call=False,
                                        )
                                        self.usage.append(usage)
                                        return InferenceResult(value, usage)
                            if self.total_used >= self.max_calls:
                                raise InferenceFailure("job_model_budget_exhausted")
                            if self.stage_used.get(task, 0) >= self.stage_limits.get(
                                task, self.max_calls
                            ):
                                raise InferenceFailure("stage_model_budget_exhausted")
                            self.total_used += 1
                            self.stage_used[task] = self.stage_used.get(task, 0) + 1
                            attempted = True
                            result = await provider.generate(system, repair_prompt, schema, task)
                            schema.model_validate(result.value.model_dump())
                        self.usage.append(replace(result.usage, retry=attempt))
                        if cacheable and self.cache:
                            await self.cache.save(key, result.value.model_dump(mode="json"))
                        return result
                    except (InferenceFailure, TimeoutError, ValidationError) as error:
                        code = (
                            error.code
                            if isinstance(error, InferenceFailure)
                            else "invalid_output"
                            if isinstance(error, ValidationError)
                            else "timeout"
                        )
                        last_code = code
                        if code in {"job_model_budget_exhausted", "stage_model_budget_exhausted"}:
                            raise
                        issues = (
                            error.issues
                            if isinstance(error, InferenceFailure)
                            else validation_issues(error)
                        )
                        self.usage.append(
                            InferenceUsage(
                                provider.name,
                                provider.model,
                                provider.credential,
                                task,
                                code,
                                int((self.clock() - start) * 1000),
                                retry=attempt,
                                validation_errors=issues if code == "invalid_output" else (),
                                model_call=attempted,
                            )
                        )
                        if provider is not self.local and code == "rate_limited":
                            delay = error.retry_after if isinstance(error, InferenceFailure) else 60
                            self.cloud_until = self.clock() + max(60, delay)
                            break  # shared account budget: never try the other key to bypass this
                        if code == "authentication":
                            self.disabled.add(provider.credential)
                            break
                        if code == "model_unavailable":
                            break
                        if code == "invalid_output":
                            repair_prompt = prompt + (
                                "\nSTRUCTURED REPAIR: previous output failed validation. "
                                "Return exactly the requested JSON object; no extra fields. "
                                "Correct these schema locations/types: "
                                + json.dumps(issues)
                                + ". Required top-level fields: "
                                + json.dumps(contract.get("required", []))
                                + ". Use target_index for compared identities and integer "
                                "evidence_indices."
                            )
                        elif code not in {"timeout", "inference_failed", "provider_http_error"}:
                            break
            raise InferenceFailure(
                "structured_output_exhausted"
                if last_code == "invalid_output"
                else "provider_unavailable",
                issues=(last_code,),
            )

    def status(self) -> dict[str, str | bool | list[str]]:
        return {
            "mode": self.mode,
            "cloud_content_allowed": self.cloud_content_allowed,
            "cloud_configured": bool(self.cloud),
            "disabled_credentials": sorted(self.disabled),
            "cloud_cooldown": self.clock() < self.cloud_until,
        }
