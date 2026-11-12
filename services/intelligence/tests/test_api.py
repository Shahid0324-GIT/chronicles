from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.application.use_cases import ListUniverses
from src.presentation.dependencies import list_universes
from tests.test_use_cases import FakeUniverses


async def test_persisted_endpoints(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/api/health")
        assert health.json() == {"status": "ok", "database": "ready"}
        catalog = await client.get("/api/universes")
        assert catalog.status_code == 200 and len(catalog.json()) == 1
        universe = await client.get("/api/universes/re-zero")
        assert universe.json()["slug"] == "re-zero"
        response = await client.get("/api/universes/re-zero/graph")
        assert response.status_code == 200
        graph = response.json()
        assert len(graph["nodes"]) == 10 and len(graph["edges"]) == 12
        assert len(graph["continuities"]) == 1
        node_id = graph["nodes"][0]["id"]
        details = await client.get(f"/api/nodes/{node_id}")
        assert details.json()["node"]["id"] == node_id
        assert "source" in graph["edges"][0] and "target" in graph["edges"][0]
        for path in [
            "/api/universes/missing",
            "/api/universes/missing/graph",
            f"/api/nodes/{uuid4()}",
        ]:
            missing = await client.get(path)
            assert missing.status_code == 404 and missing.json()["code"] == "not_found"
        invalid = await client.get("/api/nodes/not-a-uuid")
        assert invalid.status_code == 422 and invalid.json()["code"] == "invalid_request"


async def test_dependency_override_uses_fake_without_database(app):
    fake = FakeUniverses()
    app.dependency_overrides[list_universes] = lambda: ListUniverses(fake)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/universes")
        assert response.json()[0]["id"] == str(fake.universe.id)


async def test_request_repositories_share_session(factory):
    from src.presentation.dependencies import get_graph_repository, get_universe_repository

    async with factory() as session:
        assert get_universe_repository(session).session is session
        assert get_graph_repository(session).session is session


async def test_fastapi_caches_session_per_request(app):
    from src.infrastructure.persistence.repositories import (
        SqlGraphRepository,
        SqlUniverseRepository,
    )
    from src.presentation.dependencies import (
        Session,
        get_graph_repository,
        get_universe_repository,
    )

    sessions = []

    def universes(session: Session):
        sessions.append(session)
        return SqlUniverseRepository(session)

    def graph(session: Session):
        sessions.append(session)
        return SqlGraphRepository(session)

    app.dependency_overrides[get_universe_repository] = universes
    app.dependency_overrides[get_graph_repository] = graph
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/universes/re-zero/graph")).status_code == 200
    assert len(sessions) == 2 and sessions[0] is sessions[1]


async def test_database_outage_has_predictable_error(app):
    from src.presentation.dependencies import get_session

    async def unavailable():
        raise ConnectionRefusedError("Database stopped")
        yield

    app.dependency_overrides[get_session] = unavailable
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 503
        assert response.json()["code"] == "database_unavailable"
