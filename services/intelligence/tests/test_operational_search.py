"""Owned HTTP fixtures. Actual search/provider results are recorded separately."""

from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from src.application.ports.research import SearchResult
from src.application.research_contracts import InferenceFailure, ResearchPlan
from src.application.source_contracts import SourceDiscovery, SourceRegistration
from src.application.source_intelligence import SourceDiscoveryService, SourceSelector
from src.infrastructure.inference import LangChainProvider
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.source_registry import SqlSourceRegistry
from src.infrastructure.research_runtime import registry_transactions
from src.infrastructure.sources import PublicSourcePolicy, SearxngSearch, SourceRejected


async def test_discovery_keeps_successful_results_when_later_query_fails(factory):
    async with factory() as session:
        scope = await session.scalar(select(ContinuityModel))

    class Search:
        async def search(self, query, limit):
            return [r.url for r in await self.search_results(query, limit)]

        async def search_results(self, query, limit):
            if query == "later":
                raise SourceRejected("search_upstream_unavailable")
            return [SearchResult("https://owned.example/discovered", "Owned reference")]

    service = SourceDiscoveryService(Search(), registry_transactions(factory))
    with pytest.raises(SourceRejected, match="search_upstream_unavailable"):
        await service.discover(
            SourceDiscovery(
                universe_id=scope.universe_id,
                continuity_id=scope.id,
                universe_name="Owned universe",
            ),
            queries=["first", "later"],
        )
    async with factory() as session:
        entries = await SqlSourceRegistry(session).entries(scope.universe_id)
        assert any(e.url == "https://owned.example/discovered" for e in entries)
        assert all(e.retrieval_policy == "navigation-only" for e in entries)


async def test_searx_json_results_metadata_dedup_and_private_urls_are_filtered():
    body = {
        "results": [
            {
                "url": "https://public.example/page",
                "title": "Owned title",
                "content": "Owned summary",
            },
            {"url": "https://public.example/page#fragment", "title": "Duplicate"},
            {"url": "http://127.0.0.1/private"},
            {"url": "http://localhost/private"},
            {"url": "file:///private"},
            {"url": None},
        ]
    }
    real = httpx.AsyncClient

    def client(**kwargs):
        return real(
            **kwargs, transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))
        )

    with patch("src.infrastructure.sources.httpx.AsyncClient", client):
        values = await SearxngSearch(
            "http://127.0.0.1:8080", PublicSourcePolicy([]), navigation_only=True, interval=0
        ).search_results("Owned query", 5)
    assert len(values) == 1 and values[0].title == "Owned title"
    assert values[0].summary == "Owned summary"


@pytest.mark.parametrize("code", [403, 429, 503])
async def test_searx_failure_is_not_a_successful_empty_search(code):
    real = httpx.AsyncClient

    def client(**kwargs):
        return real(**kwargs, transport=httpx.MockTransport(lambda r: httpx.Response(code)))

    with patch("src.infrastructure.sources.httpx.AsyncClient", client):
        with pytest.raises(SourceRejected, match="search_unavailable"):
            await SearxngSearch("http://127.0.0.1:8080", PublicSourcePolicy([])).search("Owned", 2)


async def test_groq_health_uses_id_not_display_name():
    real = httpx.AsyncClient

    def client(**kwargs):
        return real(
            **kwargs,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json={"data": [{"id": "configured-model", "name": "Display Name"}]}
                )
            ),
        )

    provider = LangChainProvider(
        None, "groq", "configured-model", "owned", health_url="https://api.example/models"
    )
    with patch("src.infrastructure.inference.httpx.AsyncClient", client):
        assert await provider.available()


async def test_empty_results_with_upstream_errors_are_not_successful_research():
    real = httpx.AsyncClient

    def client(**kwargs):
        return real(
            **kwargs,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, json={"results": [], "unresponsive_engines": [["owned", "429"]]}
                )
            ),
        )

    with patch("src.infrastructure.sources.httpx.AsyncClient", client):
        with pytest.raises(SourceRejected, match="search_upstream_unavailable"):
            await SearxngSearch("http://127.0.0.1:8080", PublicSourcePolicy([])).search("Owned", 2)


async def test_groq_tool_validation_failure_exposes_only_schema_locations():
    class OwnedError(Exception):
        status_code = 400
        body = {
            "error": {
                "code": "tool_use_failed",
                "failed_generation": (
                    '<function=ResearchPlan>{"questions":[],"private":"SENTINEL"}</function>'
                ),
            }
        }

    class Client:
        def with_structured_output(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            raise OwnedError()

    provider = LangChainProvider(Client(), "groq", "owned", "primary", health_url="unused")
    with pytest.raises(InferenceFailure) as failure:
        await provider.generate("Owned", "Owned", ResearchPlan, "planning")
    assert failure.value.code == "invalid_output"
    assert any("questions" in issue for issue in failure.value.issues)
    assert "SENTINEL" not in repr(failure.value.issues)


async def test_discovery_inherits_only_explicit_matching_rule_and_retains_existing_permission(
    factory,
):
    async with factory() as session, session.begin():
        scope = await session.scalar(select(ContinuityModel))
        rule = SourceRegistration(
            universe_id=scope.universe_id,
            name="Owned allowed family",
            url="https://owned.example/",
            category="character-profile",
            media=[scope.medium],
            continuity_ids=[scope.id],
            access_method="html",
            authority="primary",
            retrieval_policy="permitted",
            discovery_path_prefix="/characters/",
            permission_basis="Owned synthetic permission for this path",
            attribution="Owned test",
        )
        registry = SqlSourceRegistry(session)
        await registry.register(rule)

    class Search:
        async def search_results(self, query, limit):
            return [
                SearchResult("https://owned.example/characters/mira", "Mira profile"),
                SearchResult("https://owned.example/characters-elsewhere/mira", "Outside prefix"),
                SearchResult("https://owned.example/characters/mira?private=1", "Different query"),
                SearchResult("https://another.example/characters/mira", "Other host"),
            ]

    service = SourceDiscoveryService(Search(), registry_transactions(factory))
    request = SourceDiscovery(
        universe_id=scope.universe_id, continuity_id=scope.id, universe_name="Owned universe"
    )
    values = await service.discover(request, queries=["Owned Mira profile"])
    allowed = next(v for v in values if v.name == "Mira profile")
    assert allowed.retrieval_policy == "permitted" and not allowed.cloud_content_allowed
    assert all(
        v.retrieval_policy == "navigation-only"
        for v in values
        if v.name in {"Outside prefix", "Different query", "Other host"}
    )
    assert SourceSelector().select(values, str(scope.id), "Mira", universe=scope.universe_id) == [
        allowed
    ]
    again = await service.discover(request, queries=["Owned Mira follow-up"])
    assert next(v for v in again if v.id == allowed.id).retrieval_policy == "permitted"


def test_discovery_rules_cannot_come_from_navigation_only_records():
    with pytest.raises(ValueError, match="Discovery rules"):
        SourceRegistration(
            universe_id=uuid4(),
            name="Owned reference",
            url="https://owned.example/",
            category="reference",
            media=["anime"],
            continuity_ids=[uuid4()],
            access_method="navigation",
            authority="unverified",
            discovery_path_prefix="/",
            permission_basis="Discovery metadata only",
            attribution="Owned test",
        )
