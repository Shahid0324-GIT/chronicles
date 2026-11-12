"""Owned synthetic sources and fake inference only; not the real research demonstration."""

from contextlib import asynccontextmanager
from uuid import UUID, uuid4, uuid5

import pytest
from sqlalchemy import func, select

from src.application.identity import IdentityResolver
from src.application.knowledge_contracts import IdentityComparison
from src.application.ports.knowledge import KnowledgeSession
from src.application.promotion import CanonicalGraphPromotionService
from src.application.research import ResearchRequest, SourceInput
from src.domain.entities import GraphRelationship, now
from src.domain.knowledge import (
    PromotionPolicy,
    explicit_name_bridge,
    independent_sources,
    name_key,
    order_key,
    relation_structure,
)
from src.domain.research import SourceDocument, digest, passages_for
from src.domain.value_objects import NodeType, RelationshipType
from src.infrastructure.persistence.knowledge_repository import SqlKnowledgeRepository
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, RelationshipModel
from src.infrastructure.persistence.models.knowledge import EntityAliasModel, PromotionEvidenceModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository

TEXT = (
    "Mira Vale, also known as ミラ, entered the square. "
    "Mira Vale participated in the arrival. The arrival occurred at the square. "
    "The theft preceded the search."
)


def test_names_preserve_script_but_normalize_width_punctuation_case_and_order():
    assert name_key("  ＭＩＲＡ・Vale ") == "mira vale"
    assert order_key("Vale Mira") == order_key("Mira Vale")
    assert name_key("ミラ") != name_key("Mira")
    assert explicit_name_bridge("Mira Vale", "ミラ", TEXT)
    assert not explicit_name_bridge("Mira", "Emilia", "Mira met Emilia in the square.")


@pytest.mark.parametrize(
    "decision,expected", [("SAME_ENTITY", True), ("AMBIGUOUS", False), ("DIFFERENT_ENTITY", False)]
)
async def test_evidenced_japanese_alias_resolution(decision, expected):
    universe, continuity, target = uuid4(), uuid4(), uuid4()
    source = SourceDocument(
        uuid4(),
        universe,
        continuity,
        "local:test",
        "Test",
        "Test",
        TEXT,
        digest(TEXT),
        now(),
        "Owned test source",
        "Test scope",
        False,
        False,
    )
    passage = passages_for(source)[0]
    citation = {"passage_id": str(passage.id), "quote": TEXT}
    claim = {
        "id": str(uuid4()),
        "payload": {
            "name": "ミラ",
            "type": "CHARACTER",
            "description": "Entered the square.",
            "evidence": [citation],
        },
    }

    async def infer(prompt, schema):
        return IdentityComparison(
            decision=decision,
            target_id=target,
            reason="Synthetic alias evidence.",
            evidence=[citation],
        )

    result = await IdentityResolver().resolve(
        claim,
        [
            {
                "id": str(target),
                "name": "Mira Vale",
                "type": "CHARACTER",
                "description": "Test",
                "aliases": [],
            }
        ],
        [passage],
        infer,
        continuity,
    )
    assert result["accepted"] is expected
    if expected:
        assert result["canonical_id"] == str(target)


async def test_similarity_and_shared_surnames_cannot_force_a_merge():
    continuity, target = uuid4(), uuid4()
    text = "Mira Vale and Mara Vale are two different people working at the observatory."
    source = SourceDocument(
        uuid4(),
        uuid4(),
        continuity,
        "local:test",
        "Test",
        "Test",
        text,
        digest(text),
        now(),
        "Owned test source",
        "Test scope",
        False,
        False,
    )
    passage = passages_for(source)[0]
    citation = {"passage_id": str(passage.id), "quote": text}
    claim = {
        "id": str(uuid4()),
        "payload": {
            "name": "Mara Vale",
            "type": "CHARACTER",
            "description": "Works there.",
            "evidence": [citation],
        },
    }

    async def infer(prompt, schema):
        return IdentityComparison(
            decision="SAME_ENTITY",
            target_id=target,
            reason="Deliberately wrong fake model.",
            evidence=[citation],
        )

    result = await IdentityResolver().resolve(
        claim,
        [{"id": str(target), "name": "Mira Vale", "type": "CHARACTER", "aliases": []}],
        [passage],
        infer,
        continuity,
    )
    assert not result["accepted"]


def test_causality_requires_events_and_explicit_causal_language():
    assert not relation_structure(
        RelationshipType.CAUSED, NodeType.EVENT, NodeType.EVENT, ["The theft preceded the search."]
    )
    assert relation_structure(
        RelationshipType.CAUSED, NodeType.EVENT, NodeType.EVENT, ["The theft caused the search."]
    )
    assert not relation_structure(
        RelationshipType.CAUSED, NodeType.CHARACTER, NodeType.EVENT, ["Mira caused the search."]
    )
    assert not relation_structure(
        RelationshipType.PARTICIPATED_IN, NodeType.CHARACTER, NodeType.CHARACTER, [TEXT]
    )


def test_copied_sources_and_publisher_mirrors_are_not_independent():
    assert (
        independent_sources(
            [
                {"content_hash": "one", "url": "https://a.example.org/a", "quote": TEXT},
                {"content_hash": "two", "url": "https://different.example.net/a", "quote": TEXT},
            ]
        )
        == 1
    )
    assert (
        independent_sources(
            [
                {"content_hash": "one", "url": "https://a.example.org/a"},
                {"content_hash": "two", "url": "https://b.example.org/b"},
            ]
        )
        == 1
    )


def test_policy_requires_stronger_evidence_and_never_publishes_conflicts():
    policy = PromotionPolicy()
    base = dict(
        supported=True,
        evidence_count=1,
        independent_count=1,
        identity_accepted=True,
        structural=True,
        conflict=False,
        strong=False,
        budget_available=False,
    )
    assert policy.decide(**base)[0] == "AUTO_PROMOTE"
    assert policy.decide(**{**base, "strong": True})[0] == "KEEP_UNRESOLVED"
    assert (
        policy.decide(**{**base, "conflict": True, "budget_available": True})[0]
        == "RESEARCH_FURTHER"
    )


async def prepared(factory, supported=True, label=""):
    @asynccontextmanager
    async def tx():
        async with factory() as session, session.begin():
            yield KnowledgeSession(SqlResearchRepository(session), SqlKnowledgeRepository(session))

    async with factory() as session:
        continuity = await session.scalar(select(ContinuityModel))
        universe, scope = continuity.universe_id, continuity.id
    source = SourceDocument(
        uuid5(scope, "synthetic-owned-source"),
        universe,
        scope,
        "https://owned.example.org/test",
        "Synthetic fixture",
        "Test",
        TEXT,
        digest(TEXT),
        now(),
        "Owned synthetic test source",
        "Test continuity",
        False,
        False,
    )
    passage = passages_for(source)[0]
    citation = {"passage_id": str(passage.id), "quote": TEXT}
    entities = [
        {
            "name": "Mira Vale",
            "type": "CHARACTER",
            "description": "Mira Vale entered the square.",
            "evidence": [citation],
        },
        {
            "name": "arrival",
            "type": "EVENT",
            "description": "The arrival occurred at the square.",
            "evidence": [citation],
        },
    ]
    relationship = {
        "source_name": "Mira Vale",
        "target_name": "arrival",
        "type": "PARTICIPATED_IN",
        "description": "Mira Vale participated in the arrival.",
        "evidence": [citation],
    }
    claims, resolutions = [], {}
    async with tx() as unit:
        job_id = await unit.archive.create_job(
            ResearchRequest(
                universe_id=universe,
                continuity_id=scope,
                objective="Research owned synthetic sources for testing publication. " + label,
                sources=[
                    SourceInput(
                        text=TEXT,
                        permission_basis="Owned synthetic test source",
                        source_scope="Test continuity",
                    )
                ],
            )
        )
        await unit.archive.save_source(source, [passage])
        for kind, payload in [("entity", p) for p in entities] + [("relationship", relationship)]:
            cid = uuid4()
            claim = {"id": str(cid), "kind": kind, "hash": digest(str(cid)), "payload": payload}
            claims.append(claim)
            await unit.archive.save_claim(
                job_id,
                claim,
                [{"passage_id": str(passage.id), "quote": TEXT, "start": 0, "end": len(TEXT)}],
                "supported" if supported else "insufficient",
                "Synthetic assessment only",
            )
            if kind == "entity":
                resolutions[str(cid)] = {
                    "decision": "NEW_ENTITY",
                    "accepted": True,
                    "canonical_id": str(uuid5(scope, "entity:" + str(cid))),
                    "proof": "new_scoped_entity",
                    "evidence": [citation],
                }
    service = CanonicalGraphPromotionService(tx, PromotionPolicy())
    return job_id, service, tx, claims, resolutions


async def test_atomic_promotion_idempotency_provenance_aliases_and_rollback(factory):
    job, service, tx, claims, resolutions = await prepared(factory)
    first = await service.publish(job, resolutions, {}, False)
    second = await service.publish(job, resolutions, {}, False)
    assert len(first["promoted"]) == len(second["promoted"]) == 3
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 17
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 26
        assert await session.scalar(select(func.count()).select_from(EntityAliasModel)) == 2
        assert await session.scalar(select(func.count()).select_from(PromotionEvidenceModel)) == 3
    async with tx() as unit:
        node_id = UUID(resolutions[claims[0]["id"]]["canonical_id"])
        assert len(await unit.graph.aliases(node_id, None)) == 1
        assert await unit.graph.aliases(node_id, []) == []
    reversed_records = await service.rollback_job(
        job, "Synthetic correction: withdraw fixture publications."
    )
    assert all(r["reversed"] for r in reversed_records)
    assert all(
        r["reversed"]
        for r in await service.rollback_job(job, "Repeat synthetic correction safely.")
    )
    assert not (await service.publish(job, resolutions, {}, False))["promoted"]
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 15
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 25
        assert await session.scalar(select(func.count()).select_from(PromotionEvidenceModel)) == 3


async def test_unsupported_and_contradictory_findings_do_not_block_unrelated_supported_entities(
    factory,
):
    job, service, tx, claims, resolutions = await prepared(factory)
    assessment = {claims[-1]["id"]: {"material_conflict": True}}
    result = await service.publish(job, resolutions, assessment, False)
    assert len(result["promoted"]) == 2 and len(result["unresolved"]) == 1
    async with tx() as unit:
        decisions = await unit.graph.decisions(job)
        assert decisions[claims[-1]["id"]]["policy"]["outcome"] == "KEEP_UNRESOLVED"


async def test_unsupported_cannot_be_published_even_with_accepted_identity(factory):
    job, service, _, _, resolutions = await prepared(factory, supported=False)
    assert not (await service.publish(job, resolutions, {}, False))["promoted"]


async def test_mid_transaction_failure_rolls_back_graph_aliases_and_history(factory, monkeypatch):
    job, service, tx, _, resolutions = await prepared(factory)

    async def fail(*args, **kwargs):
        raise RuntimeError("Synthetic persistence failure")

    monkeypatch.setattr(SqlKnowledgeRepository, "record", fail)
    with pytest.raises(RuntimeError, match="Synthetic"):
        await service.publish(job, resolutions, {}, False)
    async with tx() as unit:
        assert await unit.graph.records(job) == []
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 15
        assert await session.scalar(select(func.count()).select_from(EntityAliasModel)) == 0


async def test_incompatible_continuity_resolution_is_not_published(factory):
    job, service, tx, claims, resolutions = await prepared(factory)
    async with tx() as unit:
        existing = await unit.graph.node(UUID(resolutions[claims[0]["id"]]["canonical_id"]))
        assert existing is None
        resolutions[claims[0]["id"]]["decision"] = "SAME_ENTITY"
        resolutions[claims[0]["id"]]["canonical_id"] = str(uuid4())
    result = await service.publish(job, resolutions, {}, False)
    assert any(r["claim_id"] == claims[0]["id"] for r in result["unresolved"])


async def test_rollback_preserves_nodes_referenced_by_unrelated_relationships(factory):
    job, service, tx, claims, resolutions = await prepared(factory)
    await service.publish(job, resolutions, {}, False)
    a = UUID(resolutions[claims[0]["id"]]["canonical_id"])
    b = UUID(resolutions[claims[1]["id"]]["canonical_id"])
    async with tx() as unit:
        source, target = await unit.graph.node(a), await unit.graph.node(b)
        edge = GraphRelationship(
            universe_id=source.universe_id,
            continuity_id=source.continuity_id,
            source_node_id=a,
            target_node_id=b,
            relationship_type=RelationshipType.CONNECTED_TO,
            description="Independent user-authored fixture edge.",
        )
        edge.validate_endpoints(source, target)
        await unit.graph.add_edge(edge)
    await service.rollback_job(job, "Withdraw synthetic researched assertions only.")
    async with tx() as unit:
        assert await unit.graph.node(a) and await unit.graph.node(b)
