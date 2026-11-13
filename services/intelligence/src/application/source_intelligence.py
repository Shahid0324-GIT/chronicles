from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from src.application.ports.research import SearchProvider
from src.application.ports.source_intelligence import SourceRegistryTransaction
from src.application.research import SourceInput
from src.application.source_contracts import SourceDiscovery, SourceEntry, SourceRegistration


class SourceSelector:
    """Discovery priority breaks ties; it never becomes factual authority."""

    def select(
        self,
        entries: list[SourceEntry],
        continuity: str,
        topic: str,
        limit: int = 6,
        universe: UUID | None = None,
    ) -> list[SourceEntry]:
        terms = set(topic.casefold().split())
        eligible = [
            e
            for e in entries
            if (universe is None or e.universe_id == universe)
            and continuity in {str(c) for c in e.continuity_ids}
            and e.retrieval_policy == "permitted"
            and e.access_method not in {"navigation", "import"}
        ]
        authority = {"primary": 0, "secondary": 1, "unverified": 2}
        return sorted(
            eligible,
            key=lambda e: (
                -len(terms & set(" ".join(e.topics).casefold().split())),
                authority[e.authority],
                e.health == "failed",
                -e.discovery_priority,
                str(e.id),
            ),
        )[:limit]

    @staticmethod
    def input(entry: SourceEntry) -> SourceInput:
        if entry.access_method not in {"html", "mediawiki", "official-api"}:
            raise ValueError("Registry entry is not ingestible through a network adapter")
        return SourceInput(
            access_method=cast(Literal["html", "mediawiki", "official-api"], entry.access_method),
            url=entry.url,
            title=entry.name,
            permission_basis=entry.permission_basis,
            source_scope="Registry continuity: " + ",".join(map(str, entry.continuity_ids)),
            source_group=entry.derived_from,
            registry_id=entry.id,
            presentation_position=entry.presentation_position,
            position_basis=entry.position_basis,
            **entry.selectors,
        )


class SourceDiscoveryService:
    def __init__(
        self, search: SearchProvider | None, transactions: SourceRegistryTransaction
    ) -> None:
        self.search, self.transactions = search, transactions

    async def discover(
        self,
        request: SourceDiscovery,
        *,
        max_queries: int = 2,
        used_queries: list[str] | None = None,
    ) -> list[SourceEntry]:
        async with self.transactions() as registry:
            existing = await registry.entries(request.universe_id)
        # Previously inspected domains are not repeatedly searched for this universe.
        if existing or self.search is None:
            return existing
        seen: set[str] = set()
        references = []
        for suffix in ("official story episode guide", "dedicated wiki")[
            : max(0, min(max_queries, 2))
        ]:
            query = request.universe_name + " " + suffix
            if used_queries is not None:
                if query in used_queries:
                    continue
                used_queries.append(query)
            for url in (await self.search.search(query, 4))[:4]:
                host = urlsplit(url).hostname or ""
                if host in seen:
                    continue
                seen.add(host)
                references.append(
                    SourceRegistration(
                        universe_id=request.universe_id,
                        name=host,
                        url=url,
                        category="reference",
                        media=["unknown"],
                        continuity_ids=[request.continuity_id],
                        access_method="navigation",
                        authority="unverified",
                        topics=request.topics,
                        permission_basis="Discovery only; ingestion permission not established",
                        attribution="Discovered URL; verify site terms before ingestion",
                    )
                )
        async with self.transactions() as registry:
            for reference in references:
                await registry.register(reference)
            return await registry.entries(request.universe_id)
