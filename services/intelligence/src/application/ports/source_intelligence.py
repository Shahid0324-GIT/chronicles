from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from src.application.source_contracts import SourceEntry, SourceRegistration


class SourceRegistry(Protocol):
    async def register(self, entry: SourceRegistration) -> SourceEntry: ...
    async def entries(self, universe: UUID) -> list[SourceEntry]: ...
    async def health(self, identifier: UUID, error: str | None) -> None: ...


class SourceRegistryTransaction(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[SourceRegistry]: ...
