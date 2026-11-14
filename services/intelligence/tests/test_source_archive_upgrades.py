"""Owned fixtures: preserve historical evidence and recheck current source permission."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from src.application.ports.knowledge import KnowledgeSession
from src.application.promotion import CanonicalGraphPromotionService
from src.application.source_contracts import SourceRegistration
from src.application.source_intelligence import SourceSelector
from src.domain.entities import now
from src.domain.knowledge import PromotionPolicy
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.persistence.knowledge_repository import SqlKnowledgeRepository
from src.infrastructure.persistence.models import ContinuityModel, NodeModel
from src.infrastructure.persistence.models.research import SourceDocumentModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.persistence.source_registry import SqlSourceRegistry

from .test_knowledge import prepared


async def test_source_retry_window_survives_registration_and_is_cleared_on_success(factory):
    async with factory() as s, s.begin():
        scope = await s.scalar(select(ContinuityModel))
        registry = SqlSourceRegistry(s)
        registration = SourceRegistration(
            universe_id=scope.universe_id,
            name="Owned source",
            url="https://owned.example/",
            category="official",
            media=[scope.medium],
            continuity_ids=[scope.id],
            access_method="html",
            authority="primary",
            retrieval_policy="permitted",
            permission_basis="Owned fixture explicit permission",
            attribution="Owned fixture",
        )
        entry = await registry.register(registration)
        await registry.health(entry.id, "source_rate_limited", 120)
        entry = await registry.register(registration)
        assert entry.retry_at > now()
        assert not SourceSelector().select([entry], str(scope.id), "Owned")
        await registry.health(entry.id, None)
        entry = (await registry.entries(scope.universe_id))[0]
        assert entry.retry_at is None
        assert SourceSelector().select([entry], str(scope.id), "Owned")


async def test_unchanged_archive_structure_upgrade_preserves_passage_ids_and_first_retrieval(
    factory,
):
    async with factory() as s, s.begin():
        scope = await s.scalar(select(ContinuityModel))
        text = "Mira lives by the sea. Ron works in the harbor."
        source = SourceDocument(
            uuid4(),
            scope.universe_id,
            scope.id,
            "https://owned.example/doc",
            "Owned",
            "Owned",
            text,
            digest(text),
            now(),
            "Owned",
            "Owned",
            True,
            False,
            provenance={"job_id": "original", "extraction_version": "old"},
        )
        archive = SqlResearchRepository(s)
        passages = passages_for(source)
        await archive.save_source(source, passages)
        changed = replace(
            source,
            retrieved_at=source.retrieved_at + timedelta(seconds=10),
            provenance={
                "job_id": "new",
                "extraction_version": "structured-html-v4",
                "structure_text_hash": digest(text),
                "sections_json": "[]",
            },
        )
        await archive.save_source(changed, passages_for(changed, size=25))
    async with factory() as s:
        row = await s.get(SourceDocumentModel, source.id)
        assert row.provenance["job_id"] == "original"
        assert row.provenance["extraction_version"] == "structured-html-v4"
        assert row.retrieved_at.replace(tzinfo=None) == source.retrieved_at.replace(tzinfo=None)
        saved = await SqlResearchRepository(s).get_passages([source.id])
        assert [p.id for p in saved] == [p.id for p in passages]


async def test_publication_rechecks_revoked_registry_permission_and_preserves_history(factory):
    job, _, _, claims, resolutions = await prepared(factory, primary=True)
    async with factory() as s, s.begin():
        scope = await s.scalar(select(ContinuityModel))
        source = await s.get(
            SourceDocumentModel,
            UUID((await SqlResearchRepository(s).findings(job))[0]["evidence"][0]["source_id"]),
        )
        registration = SourceRegistration(
            universe_id=scope.universe_id,
            name="Owned primary",
            url=source.url,
            category="official",
            media=[scope.medium],
            continuity_ids=[scope.id],
            access_method="html",
            authority="primary",
            retrieval_policy="permitted",
            permission_basis="Owned fixture explicit permission",
            attribution="Owned fixture",
        )
        entry = await SqlSourceRegistry(s).register(registration)
        source.provenance = {**source.provenance, "registry_id": str(entry.id)}

    @asynccontextmanager
    async def tx():
        async with factory() as s, s.begin():
            yield KnowledgeSession(
                SqlResearchRepository(s), SqlKnowledgeRepository(s), SqlSourceRegistry(s)
            )

    service = CanonicalGraphPromotionService(tx, PromotionPolicy())
    assert (await service.publish(job, resolutions, {}, False))["promoted"]
    async with factory() as s, s.begin():
        await SqlSourceRegistry(s).register(
            registration.model_copy(update={"retrieval_policy": "navigation-only"})
        )
    result = await service.publish(job, resolutions, {}, False)
    assert not result["promoted"] and result["unresolved"]
    async with factory() as s:
        assert await s.scalar(select(func.count()).select_from(NodeModel)) == 15
        assert all(r["reversed"] for r in await SqlKnowledgeRepository(s).records(job))
