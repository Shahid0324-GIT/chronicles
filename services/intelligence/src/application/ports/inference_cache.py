from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol


class InferenceCache(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...
    async def save(self, key: str, payload: dict[str, Any]) -> None: ...


class InferenceCacheTransaction(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[InferenceCache]: ...
