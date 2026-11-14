"""Owned source adapters; these tests are not discovered research evidence."""

import json
import os
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from src.application.ports.research import SearchResult
from src.application.source_contracts import SourceDiscovery, SourceRegistration
from src.application.source_intelligence import DocumentLinkSearch, SourceDiscoveryService
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.source_registry import SqlSourceRegistry
from src.infrastructure.research_runtime import registry_transactions
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy


async def test_link_discovery_preserves_depth_permissions_and_persistent_url_loop_detection(
    factory,
):
    async with factory() as s, s.begin():
        scope = await s.scalar(select(ContinuityModel))
        base = dict(
            universe_id=scope.universe_id,
            url="https://owned.example/index",
            category="official",
            media=[scope.medium],
            continuity_ids=[scope.id],
            access_method="html",
            authority="primary",
            retrieval_policy="permitted",
            permission_basis="Owned fixture permits this explicit path family",
            attribution="Owned test",
            follow_links=True,
        )
        registry = SqlSourceRegistry(s)
        for prefix in ["/profiles", "/chapters"]:
            await registry.register(
                SourceRegistration(name="Owned path rule", **base, discovery_path_prefix=prefix)
            )
    links = [
        SearchResult("https://owned.example/profiles/mira", "Mira profile"),
        SearchResult("https://unknown.example/mira", "Mira reference"),
        SearchResult("http://127.0.0.1/private", "Mira private"),
        SearchResult("https://owned.example/unrelated", "Weather"),
    ]
    service = SourceDiscoveryService(DocumentLinkSearch(links), registry_transactions(factory))
    command = SourceDiscovery(
        universe_id=scope.universe_id, continuity_id=scope.id, universe_name="Owned story"
    )
    for depth in [1, 2]:
        entries = await service.discover(
            command,
            queries=["Mira"],
            max_queries=1,
            parent_url="https://owned.example/index",
            depth=depth,
        )
    actual = [e for e in entries if not e.discovery_path_prefix]
    assert len(actual) == 2
    admitted = next(e for e in actual if e.domain == "owned.example")
    assert admitted.retrieval_policy == "permitted" and admitted.discovery_depth == 1
    assert admitted.discovery_parent_url == "https://owned.example/index"
    assert not admitted.cloud_content_allowed
    assert (
        next(e for e in actual if e.domain == "unknown.example").retrieval_policy
        == "navigation-only"
    )


async def test_mediawiki_search_uses_permitted_api_and_returns_untrusted_page_leads(monkeypatch):
    requests = []

    def pinned(url, policy, maximum):
        policy.validate(url)
        requests.append(url)
        if url.endswith("robots.txt"):
            return 200, {}, b"User-agent: *\nAllow: /"
        query = parse_qs(urlsplit(url).query)
        assert query["generator"] == ["search"] and query["gsrsearch"] == ["Mira bond"]
        body = {
            "query": {
                "pages": [
                    {"title": "Mira", "fullurl": "https://wiki.owned/wiki/Mira"},
                    {"title": "Unsafe", "fullurl": "http://127.0.0.1/private"},
                ]
            }
        }
        return 200, {"content-type": "application/json"}, json.dumps(body).encode()

    monkeypatch.setattr("src.infrastructure.sources.pinned_request", pinned)
    fetcher = PublicDocumentFetcher(PublicSourcePolicy([]), 100000, 100000)
    fetcher.authorize_registered(["https://wiki.owned/api.php"])
    results = await fetcher.discover_mediawiki("https://wiki.owned/api.php", "Mira bond", 5)
    assert len(results) == 1 and results[0].title == "Mira"
    assert requests[0].endswith("robots.txt")
    assert not fetcher.policy.is_approved(results[0].url)  # Discovery is not page permission.


async def test_used_queries_do_not_consume_a_later_adapters_unspent_query_slots(factory):
    async with factory() as s:
        scope = await s.scalar(select(ContinuityModel))
    issued = []

    class Search:
        async def search(self, query, limit):
            issued.append(query)
            return ["https://owned.example/found"]

    await SourceDiscoveryService(Search(), registry_transactions(factory)).discover(
        SourceDiscovery(
            universe_id=scope.universe_id, continuity_id=scope.id, universe_name="Owned"
        ),
        queries=["used", "new useful question"],
        used_queries=["used"],
        max_queries=1,
    )
    assert issued == ["new useful question"]


async def test_illustrated_index_retains_navigation_without_creating_evidence(monkeypatch):
    from uuid import uuid4

    from src.domain.entities import now
    from src.domain.research import SourceDocument, digest, passages_for

    html = b'<html><body><nav><a href="/character/"><img alt="CHARACTER"></a></nav></body></html>'

    def pinned(url, policy, maximum):
        if url.endswith("robots.txt"):
            return 200, {}, b"User-agent: *\nAllow: /"
        return 200, {"content-type": "text/html"}, html

    monkeypatch.setattr("src.infrastructure.sources.pinned_request", pinned)
    fetcher = PublicDocumentFetcher(PublicSourcePolicy(["owned.example"]), 10000, 10000)
    document = await fetcher.fetch_complete("https://owned.example/index")
    assert document.metadata["document_role"] == "navigation-index"
    links = json.loads(document.metadata["links_json"])
    assert links[0]["text"] == "CHARACTER"
    source = SourceDocument(
        uuid4(),
        uuid4(),
        uuid4(),
        document.url,
        document.title,
        document.publisher,
        document.text,
        digest(document.text),
        now(),
        "Owned test",
        "Owned scope",
        False,
        False,
        provenance=document.metadata,
    )
    assert passages_for(source) == []


@pytest.mark.skipif(
    os.environ.get("CHRONICLES_TEST_BROWSER") != "1",
    reason="Opt-in installed Chrome fixture; no internet research",
)
async def test_controlled_rendering_uses_pinned_reader_and_blocks_private_requests(monkeypatch):
    requested = []

    def pinned(url, policy, maximum):
        policy.validate(url)
        requested.append(url)
        if url.endswith("robots.txt"):
            return 200, {}, b"User-agent: *\nAllow: /"
        if url.endswith("/app.js"):
            return (
                200,
                {"content-type": "application/javascript"},
                (
                    b"document.querySelector('main').innerHTML='<h1>Relationship</h1>"
                    b"<p>Mira helped Ron at the observatory, according to this owned fixture.</p>';"
                    b"fetch('http://127.0.0.1/private').catch(()=>{});"
                ),
            )
        return (
            200,
            {"content-type": "text/html"},
            (
                b"<html lang='en'><head><title>Owned browser fixture</title></head>"
                b"<body><main></main><script src='/app.js'></script></body></html>"
            ),
        )

    monkeypatch.setattr("src.infrastructure.sources.pinned_request", pinned)
    fetcher = PublicDocumentFetcher(PublicSourcePolicy([]), 100000, 100000)
    fetcher.authorize_registered(["https://owned.example/page"])
    result = await fetcher.fetch_rendered("https://owned.example/page")
    assert "Mira helped Ron" in result.text and result.metadata["rendered"] == "true"
    assert not any("127.0.0.1" in url for url in requested)
