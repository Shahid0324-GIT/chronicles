"""Owned fixtures, not live research or One Piece findings."""

import json
from contextlib import asynccontextmanager
from dataclasses import replace
from uuid import UUID

import pytest

from src.application.arc_contracts import ArcPlan, ArcSectionDraft, ArcUnderstanding
from src.application.arc_intelligence import ArcIntelligence, article_markdown
from src.application.encyclopedia_contracts import GroundingAssessment
from src.application.story_scope import ArcResearchScope

from .test_knowledge_presentation import fixture_knowledge, memory_atlas


def arc_fixture():
    universe, continuity, knowledge = fixture_knowledge()
    # Owned source coordinates adapted explicitly; production never converts media.
    for fact in knowledge.facts:
        fact["sources"][0]["provenance"]["position_basis"] = "manga-chapter"
    arc = ArcResearchScope(
        slug="owned-arc",
        title="Owned arc",
        continuity_id=continuity,
        first_position=1,
        last_position=7,
        references=["https://example.org/index"],
    )
    knowledge = replace(knowledge, story_scopes=[arc])
    atlas, _ = memory_atlas(knowledge)
    stored = {}

    class Repo:
        async def get(self, identifier):
            return stored.get(identifier)

        async def save(
            self,
            identifier,
            universe,
            continuity,
            resource,
            kind,
            boundary,
            revision,
            evidence,
            language,
            policy,
            payload,
            status,
            provider,
        ):
            stored[identifier] = dict(
                payload=payload,
                knowledge_revision=revision,
                evidence_fingerprint=evidence,
                grounding_status=status,
            )

    @asynccontextmanager
    async def tx():
        yield Repo()

    return ArcIntelligence(atlas, tx), universe, continuity, UUID(arc.id), knowledge, stored


def inference(calls):
    async def infer(prompt, schema, task):
        calls.append(task)
        if schema is ArcPlan:
            return ArcPlan(
                sections=[
                    dict(
                        key="entry",
                        title="Arrival at the observatory",
                        objective="Investigate entry and its missing circumstances",
                        questions=["Why enter?"],
                    )
                ]
            )
        if schema is ArcUnderstanding:
            facts = json.loads(prompt.split("\n", 1)[1])["facts"]
            return ArcUnderstanding(
                bindings=[
                    dict(
                        section_key="entry",
                        facet="action",
                        fact_ids=[f["id"] for f in facts if f["payload"].get("type") == "EVENT"],
                    )
                ]
            )
        if schema is ArcSectionDraft:
            facts = json.loads(prompt.split("\n", 1)[1])["facts"]
            return ArcSectionDraft(
                heading="Mira's arrival",
                paragraphs=[dict(text="Mira entered the observatory.", fact_ids=[facts[0]["id"]])],
            )
        if schema is GroundingAssessment:
            return GroundingAssessment(
                entailed=True,
                english=True,
                names_consistent=True,
                agency_and_tense_preserved=True,
                unsupported_relationships=False,
                reason="Owned exact accepted action",
            )
        raise AssertionError(schema)

    return infer


async def test_dossier_survives_jobs_and_unchanged_sections_reuse_without_inference():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    calls = []
    result = await service.rebuild(universe, continuity, arc, 7, inference(calls), lambda: [])
    assert result["status"] == "partial"
    dossier = result["dossier"]
    assert dossier["plan_status"] == "provisional_not_canon"
    coverage = dossier["sections"][0]["coverage"]
    assert coverage["research"] == "partial" and "consequence" in coverage["missing_facets"]
    assert not result["article"]["quality"]["complete"]
    first_calls = len(calls)
    again = await service.rebuild(universe, continuity, arc, 7, inference(calls), lambda: [])
    assert again == result and len(calls) == first_calls
    assert len(knowledge.nodes) == 2 and len(knowledge.edges) == 1
    assert "https://example.org/owned" in article_markdown(result)


async def test_changed_evidence_invalidates_reads_and_bounded_views_do_not_reuse_full_lore():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    await service.rebuild(universe, continuity, arc, None, inference([]), lambda: [])
    bounded = await service.read(universe, continuity, arc, 1)
    assert bounded["dossier"] is None
    knowledge.facts[1]["payload"]["description"] = "Mira entered a different observatory."
    assert (await service.read(universe, continuity, arc, None))["article"] is None


async def test_unknown_fact_cannot_become_dossier_knowledge():
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])

    async def malicious(prompt, schema, task):
        if schema is ArcUnderstanding:
            return ArcUnderstanding(
                bindings=[
                    dict(section_key="entry", facet="consequence", fact_ids=["invented-fact"])
                ]
            )
        return await base(prompt, schema, task)

    with pytest.raises(ValueError, match="Unlicensed dossier"):
        await service.rebuild(universe, continuity, arc, 7, malicious, lambda: [])


async def test_failed_prose_grounding_preserves_dossier_and_withholds_paragraphs():
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])

    async def reject(prompt, schema, task):
        if schema is GroundingAssessment:
            return GroundingAssessment(
                entailed=False,
                english=True,
                names_consistent=True,
                agency_and_tense_preserved=True,
                unsupported_relationships=True,
                reason="Invented causal bridge",
            )
        return await base(prompt, schema, task)

    result = await service.rebuild(universe, continuity, arc, 7, reject, lambda: [])
    assert result["dossier"]["sections"][0]["developments"]
    assert result["article"]["sections"][0]["paragraphs"] == []
    assert "Mira entered the observatory." not in article_markdown(result)
