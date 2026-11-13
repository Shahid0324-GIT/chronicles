"""Permitted API adapter behavior with owned JSON; no site access or live inference."""

import json

import pytest
from sqlalchemy import select

from src.application.source_contracts import SourceDiscovery
from src.application.source_intelligence import SourceDiscoveryService
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.research_runtime import registry_transactions
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy, SourceRejected


async def test_mediawiki_revision_page_id_and_exact_normalized_text():
    class Fetcher(PublicDocumentFetcher):
        async def _request(self, url):
            if url.endswith("robots.txt"):
                return 404, {}, b""
            return (
                200,
                {"content-type": "application/json"},
                json.dumps(
                    {
                        "query": {
                            "pages": {
                                "42": {
                                    "pageid": 42,
                                    "title": "Owned wiki page",
                                    "extract": (
                                        "Mira Vale entered the observatory."
                                        "\nOwned synthetic material."
                                    ),
                                    "revisions": [{"revid": 123}],
                                }
                            }
                        }
                    }
                ).encode(),
            )

    result = await Fetcher(PublicSourcePolicy(["example.org"]), 5000, 500).fetch_api(
        "https://example.org/api.php?action=query", "mediawiki"
    )
    assert result.metadata["page_id"] == "42" and result.metadata["revision_id"] == "123"
    assert "\n" not in result.text and result.text.startswith("Mira Vale")


async def test_api_adapter_respects_robots_before_loading_json():
    calls = []

    class Fetcher(PublicDocumentFetcher):
        async def _request(self, url):
            calls.append(url)
            return 200, {}, b"User-agent: *\nDisallow: /"

    with pytest.raises(SourceRejected, match="robots_disallowed"):
        await Fetcher(PublicSourcePolicy(["example.org"]), 5000, 500).fetch_api(
            "https://example.org/api.php", "mediawiki"
        )
    assert calls == ["https://example.org/robots.txt"]


async def test_discovery_caches_domain_references_without_granting_ingestion(factory):
    class Search:
        calls = 0

        async def search(self, query, limit):
            self.calls += 1
            return [
                "https://first.example/a",
                "https://first.example/b",
                "https://wiki.example/story",
            ]

    search = Search()
    service = SourceDiscoveryService(search, registry_transactions(factory))
    async with factory() as session, session.begin():
        scope = await session.scalar(select(ContinuityModel))
        request = SourceDiscovery(
            universe_id=scope.universe_id,
            continuity_id=scope.id,
            universe_name="Owned invented universe",
        )
    discovered = await service.discover(request)
    assert len(discovered) == 2 and search.calls == 2
    assert all(e.retrieval_policy == "navigation-only" for e in discovered)
    assert all(e.authority == "unverified" for e in discovered)
    await service.discover(request)
    assert search.calls == 2
