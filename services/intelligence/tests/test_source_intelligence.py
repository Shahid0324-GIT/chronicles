"""Owned synthetic documents and fake embeddings; not a live research result."""

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from src.application.ports.retrieval import EmbeddingIdentity
from src.application.retrieval import EvidenceRetrieval
from src.application.source_contracts import SourceEntry, SourceRegistration
from src.application.source_intelligence import SourceSelector
from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.persistence.evidence_index import SqlEvidenceIndex
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.models.source_intelligence import PassageEmbeddingModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.persistence.source_registry import SqlSourceRegistry


class FakeEmbeddings:
    def __init__(self):
        self.calls = 0
        self.revision = "owned-fake-v1"

    async def identity(self):
        return EmbeddingIdentity("test-embedding", self.revision, 3)

    async def embed(self, texts):
        self.calls += len(texts)
        return [[1.0, 0.0, 0.1] if "arrival" in t.lower() else [0.0, 1.0, 0.1] for t in texts]


async def prepare_index(factory):
    async with factory() as session, session.begin():
        scope = await session.scalar(select(ContinuityModel))
        archive = SqlResearchRepository(session)
        ids = []
        for host, text in [
            ("first.example", "Mira Vale participated in the arrival at the observatory."),
            ("second.example", "A separate history of the city and its architecture."),
        ]:
            source = SourceDocument(
                uuid4(),
                scope.universe_id,
                scope.id,
                "https://" + host,
                "Owned test",
                host,
                text,
                digest(text),
                now(),
                "Owned synthetic test source",
                "Test continuity",
                False,
                False,
                provenance={"authority": "primary"},
            )
            await archive.save_source(source, passages_for(source))
            ids.append(source.id)

    @asynccontextmanager
    async def tx():
        async with factory() as session, session.begin():
            yield SqlEvidenceIndex(session)

    embedding = FakeEmbeddings()
    return scope, ids, EvidenceRetrieval(tx, embedding), embedding


async def test_embeddings_reuse_unchanged_passages_and_reindex_model_revision(factory):
    scope, ids, service, model = await prepare_index(factory)
    first = await service.index(scope.universe_id, scope.id)
    assert first["indexed"] == 2
    calls = model.calls
    repeated = await service.index(scope.universe_id, scope.id)
    assert repeated["indexed"] == 0 and repeated["reused"] == 2 and model.calls == calls
    model.revision = "owned-fake-v2"
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 2
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(PassageEmbeddingModel)) == 4


async def test_hybrid_retrieval_exact_name_and_scope_source_filters(factory):
    scope, ids, service, _ = await prepare_index(factory)
    await service.index(scope.universe_id, scope.id)
    hits = await service.retrieve(scope.universe_id, scope.id, "arrival", names=["Mira Vale"])
    assert hits[0].source.id == ids[0]
    assert "Mira Vale" in hits[0].passage.text
    assert not await service.retrieve(scope.universe_id, uuid4(), "arrival")
    assert not await service.retrieve(uuid4(), scope.id, "arrival")
    assert not await service.retrieve(scope.universe_id, scope.id, "arrival", allowed_sources=[])
    assert not await service.retrieve(
        scope.universe_id, scope.id, "arrival", authorities=["secondary"]
    )


async def test_invalid_vector_dimensions_do_not_persist(factory):
    scope, _, service, model = await prepare_index(factory)
    async with service.transactions() as repo:
        hit = (await repo.passages(scope.universe_id, scope.id))[0]
        with pytest.raises(ValueError, match="Invalid vector"):
            await repo.store(hit, await model.identity(), [1.0, 0.0])


async def test_unchanged_revision_reuses_vector_and_revoked_registry_blocks_retrieval(factory):
    from dataclasses import replace

    from src.infrastructure.persistence.models.research import SourceDocumentModel

    scope, ids, service, model = await prepare_index(factory)
    await service.index(scope.universe_id, scope.id)
    async with service.transactions() as repo:
        original = (await repo.passages(scope.universe_id, scope.id, [ids[0]]))[0].source
    duplicate = replace(original, id=uuid4(), url=original.url + "/revision-v2")
    async with factory() as session, session.begin():
        await SqlResearchRepository(session).save_source(duplicate, passages_for(duplicate))
        config = SourceRegistration(
            universe_id=scope.universe_id,
            name="Owned revision",
            url=duplicate.url,
            category="reference",
            media=["anime"],
            continuity_ids=[scope.id],
            access_method="html",
            authority="primary",
            retrieval_policy="permitted",
            permission_basis="Owned test permission",
            attribution="Owned synthetic source",
        )
        entry = await SqlSourceRegistry(session).register(config)
        row = await session.get(SourceDocumentModel, duplicate.id)
        row.provenance = {**row.provenance, "registry_id": str(entry.id)}
    calls = model.calls
    result = await service.index(scope.universe_id, scope.id, [duplicate.id])
    assert result["indexed"] == 0 and result["reused"] == 1 and model.calls == calls
    async with factory() as session, session.begin():
        await SqlSourceRegistry(session).register(
            config.model_copy(update={"retrieval_policy": "navigation-only"})
        )
    assert not await service.retrieve(
        scope.universe_id, scope.id, "arrival", allowed_sources=[duplicate.id]
    )
    assert model.calls == calls


async def test_registry_preserves_access_authority_dedup_and_health(factory):
    async with factory() as session, session.begin():
        scope = await session.scalar(select(ContinuityModel))
        registry = SqlSourceRegistry(session)
        config = SourceRegistration(
            universe_id=scope.universe_id,
            name="Owned guide",
            url="https://example.org/guide#section",
            category="episode-guide",
            media=["anime"],
            continuity_ids=[scope.id],
            access_method="html",
            authority="primary",
            retrieval_policy="permitted",
            permission_basis="Owned synthetic permission",
            attribution="Owned test source",
            topics=["arrival"],
        )
        first = await registry.register(config)
        assert first.id == (await registry.register(config)).id
        assert len(await registry.entries(scope.universe_id)) == 1
        await registry.health(first.id, "robots_disallowed")
        failed = (await registry.entries(scope.universe_id))[0]
        assert failed.health == "failed" and failed.last_success is None
        await registry.health(first.id, None)
        assert (await registry.entries(scope.universe_id))[0].last_success is not None
        other = config.model_copy(update={"continuity_ids": [uuid4()]})
        with pytest.raises(Exception, match="continuity"):
            await registry.register(other)


def test_source_selection_never_confuses_discovery_priority_with_authority():
    universe, continuity = uuid4(), uuid4()

    def entry(authority, priority, policy="permitted", scope=continuity):
        return SourceEntry(
            id=uuid4(),
            universe_id=universe,
            name="Owned guide",
            url="https://example.org/guide",
            domain="example.org",
            category="reference",
            media=["anime"],
            continuity_ids=[scope],
            access_method="html",
            authority=authority,
            discovery_priority=priority,
            retrieval_policy=policy,
            permission_basis="Owned test source policy",
            attribution="Owned",
            health="unknown",
            last_success=None,
            last_error=None,
        )

    primary, secondary = entry("primary", 1), entry("secondary", 100)
    chosen = SourceSelector().select(
        [
            secondary,
            primary,
            entry("primary", 100, "navigation-only"),
            entry("primary", 100, scope=uuid4()),
        ],
        str(continuity),
        "story",
    )
    assert [c.id for c in chosen] == [primary.id, secondary.id]


def test_chunking_keeps_exact_offsets_and_prefers_sentence_boundaries():
    text = "Mira arrived at the observatory. " * 12
    source = SourceDocument(
        uuid4(),
        uuid4(),
        uuid4(),
        "https://example.org",
        "Owned",
        "Owned",
        text,
        digest(text),
        now(),
        "Owned permission",
        "Owned scope",
        False,
        False,
    )
    chunks = passages_for(source, 100)
    assert "".join(c.text for c in chunks) == text
    assert all(source.text[c.start : c.end] == c.text for c in chunks)
    assert chunks[0].text.endswith(". ")


def test_explicit_reading_and_bilingual_annotations_form_a_source_bridge():
    from src.domain.knowledge import same_event_context, source_name_bridge

    assert source_name_bridge(
        "源名",
        "Source Person",
        ["源名（ヨミ）が訪れた。", "ゲン・ヨミ Source Person is named in this owned profile."],
    )
    assert not source_name_bridge("源名", "Source Person", ["源名 met Source Person."])
    left = {
        "source_id": "owned-source",
        "trigger_start": 10,
        "trigger_end": 20,
        "participants": ["Mira Vale"],
        "location": "Observatory",
    }
    assert same_event_context(left, {**left, "trigger_end": 25})
    assert not same_event_context(left, {**left, "trigger_start": 30, "trigger_end": 40})
    assert not same_event_context(left, {**left, "participants": ["Another Vale"]})
