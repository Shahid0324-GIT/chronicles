from typing import Any

from src.application.ports.inference_cache import InferenceCacheTransaction


class StoredInferenceCache:
    """Own short cache transactions; model calls happen after these methods return."""

    def __init__(self, transactions: InferenceCacheTransaction) -> None:
        self.transactions = transactions

    async def get(self, key: str) -> dict[str, Any] | None:
        async with self.transactions() as cache:
            return await cache.get(key)

    async def save(self, key: str, payload: dict[str, Any]) -> None:
        async with self.transactions() as cache:
            await cache.save(key, payload)
