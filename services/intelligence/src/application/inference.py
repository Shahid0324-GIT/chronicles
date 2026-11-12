import asyncio
from collections.abc import Callable
from time import monotonic

from src.application.research_contracts import (
    InferenceFailure,
    InferenceProvider,
    InferenceResult,
    InferenceUsage,
    T,
    Task,
)


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
    ) -> None:
        self.local, self.cloud = local, cloud
        self.mode, self.cloud_content_allowed = mode, cloud_content_allowed
        self.attempts, self.timeout, self.clock = attempts, timeout, clock
        self.gate = asyncio.Semaphore(concurrency)
        self.cloud_until = 0.0
        self.disabled: set[str] = set()
        self.usage: list[InferenceUsage] = []

    async def generate(
        self,
        system: str,
        prompt: str,
        schema: type[T],
        task: Task,
        *,
        public_source_content: bool = False,
    ) -> InferenceResult:
        eligible = self.mode != "local" and self.cloud_content_allowed and public_source_content
        prefer_cloud = eligible and (self.mode == "cloud" or task == "verification")
        candidates = [self.local]
        if prefer_cloud and self.clock() >= self.cloud_until:
            candidate = next((p for p in self.cloud if p.credential not in self.disabled), None)
            if candidate:
                candidates.insert(0, candidate)
        async with self.gate:
            for provider in candidates:
                for _ in range(self.attempts):
                    start = self.clock()
                    try:
                        async with asyncio.timeout(self.timeout):
                            if not await provider.available():
                                raise InferenceFailure("model_unavailable")
                            result = await provider.generate(system, prompt, schema, task)
                            schema.model_validate(result.value.model_dump())
                        self.usage.append(result.usage)
                        return result
                    except (InferenceFailure, TimeoutError) as error:
                        code = error.code if isinstance(error, InferenceFailure) else "timeout"
                        self.usage.append(
                            InferenceUsage(
                                provider.name,
                                provider.model,
                                provider.credential,
                                task,
                                code,
                                int((self.clock() - start) * 1000),
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
            raise InferenceFailure("no_provider_succeeded")

    def status(self) -> dict[str, str | bool | list[str]]:
        return {
            "mode": self.mode,
            "cloud_content_allowed": self.cloud_content_allowed,
            "cloud_configured": bool(self.cloud),
            "disabled_credentials": sorted(self.disabled),
            "cloud_cooldown": self.clock() < self.cloud_until,
        }
