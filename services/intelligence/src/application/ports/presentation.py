from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol
from uuid import UUID


class PresentationRepository(Protocol):
    async def get(self, identifier: UUID) -> dict[str, Any] | None: ...
    async def save(
        self,
        identifier: UUID,
        universe: UUID,
        continuity: UUID,
        resource: UUID,
        kind: str,
        boundary: str,
        revision: str,
        evidence: str,
        language: str,
        policy: str,
        payload: dict[str, Any],
        status: str,
        provider: list[dict[str, Any]],
    ) -> None: ...


class PresentationTransaction(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[PresentationRepository]: ...
