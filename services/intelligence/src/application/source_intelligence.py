from collections.abc import Awaitable, Callable
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from src.application.ports.research import SearchProvider
from src.application.ports.source_intelligence import SourceRegistryTransaction
from src.application.research import SourceInput
from src.application.research_frontier import terms
from src.application.research_policy import UniverseResearchProfile
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
        profile: UniverseResearchProfile | None = None,
    ) -> list[SourceEntry]:
        return [entry for entry, _, _ in self.rank(entries, continuity, topic, universe, profile)][
            :limit
        ]

    def rank(
        self,
        entries: list[SourceEntry],
        continuity: str,
        topic: str,
        universe: UUID | None = None,
        profile: UniverseResearchProfile | None = None,
    ) -> list[tuple[SourceEntry, float, list[str]]]:
        """Permission is a gate. Continuity authority, relevance and novelty are distinct."""
        query_terms = terms(topic)
        eligible = [
            e
            for e in entries
            if (universe is None or e.universe_id == universe)
            and continuity in {str(c) for c in e.continuity_ids}
            and e.retrieval_policy == "permitted"
            and e.access_method not in {"navigation", "import"}
        ]
        ranked = []
        for entry in eligible:
            relevance = len(query_terms & terms(entry.name + " " + " ".join(entry.topics)))
            authority = {"primary": 8, "secondary": 4, "unverified": 0}[entry.authority]
            priority = (profile.source_priorities.get(entry.category, 0) if profile else 0) / 10
            score = relevance * 10 + authority + priority + entry.discovery_priority / 100
            if entry.health == "failed":
                score -= 20
            ranked.append(
                (
                    entry,
                    score,
                    [
                        f"relevance:{relevance}",
                        f"authority:{entry.authority}",
                        "continuity-compatible",
                        "retrieval-permitted",
                        f"profile-priority:{priority}",
                    ],
                )
            )
        # Diversify source families; derivative publishers cannot inflate corroboration.
        ordered = []
        groups: set[str] = set()
        while ranked:
            selected = max(
                ranked,
                key=lambda item: (
                    item[1] - (6 if (item[0].derived_from or item[0].domain) in groups else 0),
                    str(item[0].id),
                ),
            )
            ranked.remove(selected)
            group = selected[0].derived_from or selected[0].domain
            ordered.append(
                (
                    selected[0],
                    selected[1],
                    [
                        *selected[2],
                        "repeated-source-family" if group in groups else "new-source-family",
                    ],
                )
            )
            groups.add(group)
        return ordered

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
        queries: list[str] | None = None,
        on_query: Callable[[str], Awaitable[None]] | None = None,
    ) -> list[SourceEntry]:
        async with self.transactions() as registry:
            existing = await registry.entries(request.universe_id)
        # Previously inspected domains are not repeatedly searched for this universe.
        if self.search is None or (existing and queries is None):
            return existing
        seen: set[str] = set()
        references = []
        candidates = (
            queries
            if queries is not None
            else [
                request.universe_name + " official source material",
                request.universe_name + " dedicated encyclopedia references",
            ]
        )
        for query in candidates[: max(0, max_queries)]:
            if used_queries is not None:
                if query in used_queries:
                    continue
                used_queries.append(query)
            if on_query:
                await on_query(query)
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
                        discovery_origin=query,
                    )
                )
        async with self.transactions() as registry:
            for reference in references:
                await registry.register(reference)
            return await registry.entries(request.universe_id)
