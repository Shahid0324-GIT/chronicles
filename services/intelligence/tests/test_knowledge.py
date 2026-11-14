"""Owned synthetic sources and fake inference only; not the real research demonstration."""

from contextlib import asynccontextmanager
from uuid import UUID, uuid4, uuid5

import pytest
from sqlalchemy import func, select

from src.application.identity import IdentityResolver
from src.application.knowledge_contracts import (
    EmptyCatalogIdentityComparison,
    IdentityComparison,
)
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


async def test_empty_catalog_cannot_supply_invented_identity_targets():
    from pydantic import ValidationError

    universe, continuity = uuid4(), uuid4()
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
    claim = {
        "id": str(uuid4()),
        "payload": {
            "name": "Mira Vale",
            "type": "CHARACTER",
            "description": "Entered the square.",
            "evidence": [{"passage_id": str(passage.id), "quote": TEXT}],
        },
    }

    async def infer(prompt, schema):
        assert schema is EmptyCatalogIdentityComparison
        values = dict(
            entity_type_valid=True,
            reason="Owned source identifies a person.",
            evidence_indices=[0],
            hidden_identity=False,
        )
        with pytest.raises(ValidationError):
            schema(decision="SAME_ENTITY", target_index=0, **values)
        return schema(decision="NEW_ENTITY", target_index=None, **values)

    result = await IdentityResolver().resolve(
        claim, [], [passage], infer, continuity, indexed_evidence=True
    )
    assert result["accepted"] and result["proof"] == "new_scoped_entity"
    assert result["canonical_id"] is not None


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
            entity_type_valid=True,
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
            entity_type_valid=True,
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
    second_text = (
        "Mira Vale entered the square during the arrival at that place. "
        "This account names the participant."
    )
    second_source = SourceDocument(
        uuid5(scope, "synthetic-second-source"),
        universe,
        scope,
        "https://independent.example.net/story",
        "Second owned fixture",
        "Independent test publisher",
        second_text,
        digest(second_text),
        now(),
        "Owned synthetic test material",
        "Test continuity",
        False,
        False,
    )
    second_passage = passages_for(second_source)[0]
    citation = {"passage_id": str(passage.id), "quote": TEXT}
    second_citation = {"passage_id": str(second_passage.id), "quote": second_text}
    entities = [
        {
            "name": "Mira Vale",
            "type": "CHARACTER",
            "description": "Mira Vale entered the square.",
            "evidence": [citation, second_citation],
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
        await unit.archive.save_source(second_source, [second_passage])
        for kind, payload in [("entity", p) for p in entities] + [("relationship", relationship)]:
            cid = uuid4()
            claim = {"id": str(cid), "kind": kind, "hash": digest(str(cid)), "payload": payload}
            claims.append(claim)
            await unit.archive.save_claim(
                job_id,
                claim,
                [
                    {
                        "passage_id": c["passage_id"],
                        "quote": c["quote"],
                        "start": 0,
                        "end": len(c["quote"]),
                    }
                    for c in payload["evidence"]
                ],
                "supported" if supported else "insufficient",
                "Synthetic assessment only",
            )
            if kind == "entity":
                resolutions[str(cid)] = {
                    "decision": "NEW_ENTITY",
                    "accepted": True,
                    "entity_type_valid": True,
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
        assert await session.scalar(select(func.count()).select_from(PromotionEvidenceModel)) == 4
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
        assert await session.scalar(select(func.count()).select_from(PromotionEvidenceModel)) == 4


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


async def test_type_mismatch_cannot_publish_even_when_claim_is_labeled_supported(factory):
    job, service, _, claims, resolutions = await prepared(factory)
    resolutions[claims[0]["id"]]["entity_type_valid"] = False
    result = await service.publish(job, resolutions, {}, False)
    assert len(result["promoted"]) == 1  # The unrelated, correctly typed event survives.
    assert len(result["unresolved"]) == 2


async def test_hidden_identity_requires_additional_independent_evidence(factory):
    job, service, _, claims, resolutions = await prepared(factory)
    resolutions[claims[0]["id"]]["hidden_identity"] = True
    service.policy = PromotionPolicy(strong_sources=3)
    result = await service.publish(job, resolutions, {}, False)
    assert any(r["claim_id"] == claims[0]["id"] for r in result["unresolved"])
    assert len(result["promoted"]) == 1


async def test_targeted_rollback_does_not_withdraw_unrelated_claims(factory):
    job, service, tx, claims, resolutions = await prepared(factory)
    result = await service.publish(job, resolutions, {}, False)
    edge = next(r for r in result["promoted"] if r["kind"] == "relationship")
    await service.rollback_promotion(UUID(edge["id"]), "Withdraw one synthetic relationship only.")
    async with tx() as unit:
        records = await unit.graph.records(job)
        assert sum(r["reversed"] for r in records) == 1
        assert sum(not r["reversed"] for r in records) == 2
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 17
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 25


async def test_replay_rechecks_evidence_and_withdraws_newly_contradicted_publication(factory):
    job, service, tx, claims, resolutions = await prepared(factory)
    await service.publish(job, resolutions, {}, False)
    result = await service.publish(
        job, resolutions, {claims[-1]["id"]: {"material_conflict": True}}, False
    )
    assert len(result["promoted"]) == 2
    async with tx() as unit:
        records = await unit.graph.records(job)
        assert next(r for r in records if r["kind"] == "relationship")["reversed"]


@pytest.mark.parametrize(
    "kind,name,description",
    [
        ("EVENT", "第3話", "An episode title is not an in-world event."),
        ("EVENT", "Episode 2", "An episode number is publication metadata."),
        ("LOCATION", "Cafe", "TVアニメ初イベント＆コラボカフェの開催決定！"),
    ],
)
def test_publication_metadata_is_not_in_world_knowledge(kind, name, description):
    from src.domain.knowledge import in_world_structure

    assert not in_world_structure({"type": kind, "name": name, "description": description}, [])


def test_causality_preserves_direction_and_rejects_negation():
    text = ["The theft caused the search."]
    assert relation_structure(
        RelationshipType.CAUSED, NodeType.EVENT, NodeType.EVENT, text, "theft", "search"
    )
    assert not relation_structure(
        RelationshipType.CAUSED, NodeType.EVENT, NodeType.EVENT, text, "search", "theft"
    )
    assert not relation_structure(
        RelationshipType.CAUSED,
        NodeType.EVENT,
        NodeType.EVENT,
        ["The theft never caused the search."],
        "theft",
        "search",
    )


async def test_supported_causality_requires_two_distinct_uncopied_sources(factory):
    from src.infrastructure.research_runtime import knowledge_transactions

    tx = knowledge_transactions(factory)
    async with factory() as session:
        scope = await session.scalar(select(ContinuityModel))
    texts = [
        "The theft directly caused the search to begin.",
        "Because thieves stole a badge, a search began in response to that theft.",
    ]
    documents = [
        SourceDocument(
            uuid4(),
            scope.universe_id,
            scope.id,
            f"https://publisher-{index}.example{'org' if index == 0 else 'net'}/story",
            "Owned synthetic source",
            "Test publisher",
            value,
            digest(value),
            now(),
            "Owned synthetic test material",
            "Synthetic continuity",
            False,
            False,
        )
        for index, value in enumerate(texts)
    ]
    passages = [passages_for(document)[0] for document in documents]
    citations = [{"passage_id": str(p.id), "quote": p.text} for p in passages]
    resolutions = {}
    async with tx() as unit:
        job = await unit.archive.create_job(
            ResearchRequest(
                universe_id=scope.universe_id,
                continuity_id=scope.id,
                objective="Verify a causal assertion in owned synthetic text.",
                sources=[
                    SourceInput(
                        text=texts[0],
                        permission_basis="Owned synthetic test source",
                        source_scope="Synthetic continuity",
                    )
                ],
            )
        )
        for document, passage in zip(documents, passages, strict=True):
            await unit.archive.save_source(document, [passage])
        for kind, payload in [
            (
                "entity",
                {
                    "name": "theft",
                    "type": "EVENT",
                    "description": "A theft occurred.",
                    "evidence": citations[:1],
                },
            ),
            (
                "entity",
                {
                    "name": "search",
                    "type": "EVENT",
                    "description": "A search followed the theft.",
                    "evidence": citations[:1],
                },
            ),
            (
                "relationship",
                {
                    "source_name": "theft",
                    "target_name": "search",
                    "type": "CAUSED",
                    "description": "The theft caused the search.",
                    "evidence": citations,
                },
            ),
        ]:
            cid = uuid4()
            claim = {"id": str(cid), "kind": kind, "hash": digest(str(cid)), "payload": payload}
            evidence = [
                {
                    "passage_id": c["passage_id"],
                    "quote": c["quote"],
                    "start": 0,
                    "end": len(c["quote"]),
                }
                for c in payload["evidence"]
            ]
            await unit.archive.save_claim(
                job, claim, evidence, "supported", "Synthetic semantic assessment"
            )
            if kind == "entity":
                resolutions[str(cid)] = {
                    "decision": "NEW_ENTITY",
                    "accepted": True,
                    "entity_type_valid": True,
                    "canonical_id": str(uuid5(scope.id, "entity:" + str(cid))),
                    "proof": "new_scoped_entity",
                    "evidence": citations[:1],
                }
    service = CanonicalGraphPromotionService(tx, PromotionPolicy())
    result = await service.publish(job, resolutions, {}, False)
    assert len(result["promoted"]) == 3
    edge = next(r for r in result["promoted"] if r["kind"] == "relationship")
    async with tx() as unit:
        decision = (await unit.graph.decisions(job))[edge["claim_id"]]
        assert decision["policy"]["independent_sources"] == 2


def test_declared_groups_merge_sources_but_never_split_one_publisher():
    assert (
        independent_sources(
            [
                {
                    "content_hash": "one",
                    "url": "https://a.example.org/one",
                    "independence_key": "group-one",
                },
                {
                    "content_hash": "two",
                    "url": "https://b.example.org/two",
                    "independence_key": "group-two",
                },
            ]
        )
        == 1
    )
    assert (
        independent_sources(
            [
                {
                    "content_hash": "one",
                    "url": "https://first.example.org/one",
                    "independence_key": "shared-origin",
                },
                {
                    "content_hash": "two",
                    "url": "https://second.example.net/two",
                    "independence_key": "shared-origin",
                },
            ]
        )
        == 1
    )
