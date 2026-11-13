import asyncio
import math
from contextlib import nullcontext

import httpx

from src.application.ports.model_runtime import ModelLease
from src.application.ports.retrieval import EmbeddingIdentity


class OllamaEmbeddings:
    """Sequential local batches, measured dimensions and a content-addressed model version."""

    def __init__(self, base_url: str, model: str, lease: ModelLease | None = None) -> None:
        self.url, self.model = base_url.rstrip("/"), model
        self.lock = asyncio.Lock()
        self._identity: EmbeddingIdentity | None = None
        self.lease = lease

    async def identity(self) -> EmbeddingIdentity:
        async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
            tags = await client.get(self.url + "/api/tags")
            tags.raise_for_status()
        digest = next(m["digest"] for m in tags.json()["models"] if m["name"] == self.model)
        if self._identity is None or self._identity.digest != digest:
            self._identity = None
            vector = (await self.embed(["Embedding dimension probe."]))[0]
            self._identity = EmbeddingIdentity(self.model, digest, len(vector))
        return self._identity

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts or len(texts) > 4:
            raise ValueError("Embedding batch must contain one to four passages")
        async with (
            self.lock,
            self.lease() if self.lease else nullcontext(),
            httpx.AsyncClient(timeout=180, trust_env=False) as client,
        ):
            response = await client.post(
                self.url + "/api/embed",
                json={"model": self.model, "input": texts, "truncate": False, "keep_alive": 0},
            )
            response.raise_for_status()
        vectors = [[float(x) for x in row] for row in response.json()["embeddings"]]
        if len(vectors) != len(texts) or any(
            not v or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors
        ):
            raise ValueError("Invalid embedding response")
        if len({len(v) for v in vectors}) != 1 or (
            self._identity and len(vectors[0]) != self._identity.dimensions
        ):
            raise ValueError("Embedding dimensions changed; start a new model version")
        return vectors
