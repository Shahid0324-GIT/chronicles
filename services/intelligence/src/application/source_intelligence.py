import ipaddress
from collections.abc import Awaitable, Callable
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from src.application.ports.research import MetadataSearchProvider, SearchProvider, SearchResult
from src.application.ports.source_intelligence import SourceRegistryTransaction
from src.application.research import SourceInput
from src.application.research_frontier import terms
from src.application.research_policy import UniverseResearchProfile
from src.application.source_contracts import SourceDiscovery, SourceEntry, SourceRegistration


class DocumentLinkSearch:
    """Actual links from a retrieved document, ranked as leads rather than search proof."""

    def __init__(self, links: list[SearchResult]) -> None:
        self.links = links

    async def search(self, query: str, limit: int) -> list[str]:
        return [item.url for item in await self.search_results(query, limit)]

    async def search_results(self, query: str, limit: int) -> list[SearchResult]:
        words = terms(query)
        relevant = []
        for link in self.links:
            p = urlsplit(link.url)
            host = p.hostname or ""
            try:
                public = ipaddress.ip_address(host).is_global
            except ValueError:
                public = (
                    bool(host)
                    and host != "localhost"
                    and not host.endswith((".local", ".internal", ".localhost"))
                )
            if (
                p.scheme not in {"http", "https"}
                or p.username
                or p.password
                or not public
                or not words & terms(link.title + " " + link.summary)
            ):
                continue
            relevant.append(link)
        return sorted(
            relevant, key=lambda r: (-len(words & terms(r.title + " " + r.summary)), r.url)
        )[:limit]


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
            and e.discovery_path_prefix is None
            and (profile is None or e.access_method in profile.retrieval_methods)
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

    @staticmethod
    def category(
        url: str,
    ) -> Literal[
        "reference", "dedicated-wiki", "character-profile", "chapter-index", "item-description"
    ]:
        path = urlsplit(url).path.casefold()
        if "/wiki/" in path:
            return "dedicated-wiki"
        if "character" in path:
            return "character-profile"
        if "chapter" in path:
            return "chapter-index"
        if "artifact" in path or "weapon" in path or "item" in path:
            return "item-description"
        return "reference"

    async def discover(
        self,
        request: SourceDiscovery,
        *,
        max_queries: int = 2,
        used_queries: list[str] | None = None,
        queries: list[str] | None = None,
        on_query: Callable[[str], Awaitable[None]] | None = None,
        on_results: Callable[[str, list[SearchResult]], Awaitable[None]] | None = None,
        parent_url: str | None = None,
        depth: int = 0,
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
            results = (
                await self.search.search_results(query, 8)
                if isinstance(self.search, MetadataSearchProvider)
                else [SearchResult(url) for url in (await self.search.search(query, 4))[:4]]
            )
            if on_results:
                await on_results(query, results)
            for result in results:
                url = result.url
                host = urlsplit(url).hostname or ""
                identity = url if isinstance(self.search, MetadataSearchProvider) else host
                if identity in seen:
                    continue
                seen.add(identity)
                parsed = urlsplit(url)
                known = [entry for entry in existing if entry.url.partition("#")[0] == url]
                if known and (
                    parent_url or not any(request.continuity_id in e.continuity_ids for e in known)
                ):
                    continue  # Persistent URL index: no linked loops or scope overwrites.
                if any(entry.retrieval_policy == "permitted" for entry in known):
                    continue  # Discovery cannot erase existing permission or source selections.
                rules = [
                    entry
                    for entry in existing
                    if entry.retrieval_policy == "permitted"
                    and entry.discovery_path_prefix
                    and request.continuity_id in entry.continuity_ids
                    and urlsplit(entry.url).scheme == parsed.scheme
                    and urlsplit(entry.url).netloc == parsed.netloc
                    and urlsplit(entry.url).query == parsed.query
                    and (
                        parsed.path.rstrip("/") == entry.discovery_path_prefix.rstrip("/")
                        or parsed.path.startswith(entry.discovery_path_prefix.rstrip("/") + "/")
                    )
                ]
                if rules:
                    longest = max(len(entry.discovery_path_prefix or "") for entry in rules)
                    for template in rules:
                        if len(template.discovery_path_prefix or "") != longest:
                            continue
                        data = {
                            key: value
                            for key, value in template.model_dump(mode="json").items()
                            if key in SourceRegistration.model_fields
                        }
                        data.update(
                            url=url,
                            name=result.title or host,
                            discovery_origin=query,
                            discovery_summary=result.summary,
                            discovery_path_prefix=None,
                            discovery_parent_url=parent_url,
                            discovery_depth=depth,
                            permission_basis=(
                                "Approved discovery rule "
                                + str(template.id)
                                + ": "
                                + template.permission_basis
                            )[:500],
                        )
                        references.append(SourceRegistration.model_validate(data))
                    continue
                references.append(
                    SourceRegistration(
                        universe_id=request.universe_id,
                        name=result.title or host,
                        url=url,
                        category=self.category(url),
                        media=["unknown"],
                        continuity_ids=[request.continuity_id],
                        access_method="navigation",
                        authority="unverified",
                        topics=request.topics,
                        permission_basis="Discovery only; ingestion permission not established",
                        attribution="Discovered URL; verify site terms before ingestion",
                        discovery_origin=query,
                        discovery_summary=result.summary,
                        discovery_parent_url=parent_url,
                        discovery_depth=depth,
                    )
                )
            # Retain successful discoveries even if a later engine request fails.
            async with self.transactions() as registry:
                for reference in references:
                    await registry.register(reference)
            references.clear()
        async with self.transactions() as registry:
            return await registry.entries(request.universe_id)
