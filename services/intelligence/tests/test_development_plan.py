"""Owned deterministic controls, not evidence of real research quality."""

from uuid import uuid4

import pytest

from src.application.arc_contracts import DevelopmentEvidence
from src.application.development_plan import (
    PlanAssessment,
    PlanProposal,
    assess_plan,
    layers,
    plan_from_proposal,
)


def material():
    source, continuity, arc, section = uuid4(), uuid4(), uuid4(), uuid4()
    statements = ["Mira tried to open the gate.", "Ron opened the gate."]
    evidence = [
        DevelopmentEvidence(
            id=str(i + 1),
            source_id=source,
            source_hash="owned",
            passage_id=uuid4(),
            passage_hash="owned",
            passage_start=100,
            start=100 + i * 40,
            end=100 + i * 40 + len(text),
            text=text,
            source_group="owned",
            eligibility_boundary=2,
            position_basis="manga-chapter",
        )
        for i, text in enumerate(statements)
    ]
    facts = [
        {"id": f"f{i}", "payload": {"description": text}, "sources": [{"id": str(source)}]}
        for i, text in enumerate(statements)
    ]
    proposal = PlanProposal.model_validate(
        {
            "developments": [
                {
                    "key": f"d{i}",
                    "title": text,
                    "anchor_ids": [str(i + 1)],
                    "clauses": [
                        {
                            "fact_id": f"f{i}",
                            "clause": text,
                            "facet": "action",
                            "modality": "attempted" if i == 0 else "completed",
                            "negated": False,
                            "evidence_ids": [str(i + 1)],
                        }
                    ],
                }
                for i, text in reversed(list(enumerate(statements)))
            ]
        }
    )
    return proposal, facts, evidence, arc, section, continuity


def test_source_order_is_independent_of_model_array_order_and_not_world_time():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    keys = {d.id: d.key for d in plan.developments}
    lane = next(iter(plan.source_lanes.values()))
    assert [[keys[i] for i in group] for group in lane] == [["d0"], ["d1"]]
    assert all(o.kind == "reference_presentation" for o in plan.ordering)
    assert all(
        d.in_world_position is None and d.revelation_position is None for d in plan.developments
    )
    assert plan.structural.status == "pending"  # Geometry alone is not semantic proof.
    assert plan_from_proposal(proposal, facts, evidence, *scope).revision == plan.revision


def test_incomparable_source_lanes_do_not_create_cross_source_chronology():
    proposal, facts, evidence, *scope = material()
    evidence[1].source_id = uuid4()
    facts[1]["sources"][0]["id"] = str(evidence[1].source_id)
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    assert not plan.ordering and len(plan.source_lanes) == 2
    a, b = uuid4(), uuid4()
    assert len(layers([a, b], [])[0]) == 2
    with pytest.raises(ValueError, match="Cyclic"):
        layers([a, b], [(a, b), (b, a)])


def test_changed_clause_unknown_evidence_and_unaccounted_facts_are_rejected():
    proposal, facts, evidence, *scope = material()
    proposal.developments[0].clauses[0].clause = "Ron killed Mira."
    with pytest.raises(ValueError, match="exact accepted"):
        plan_from_proposal(proposal, facts, evidence, *scope)
    proposal, facts, evidence, *scope = material()
    proposal.developments.pop()
    with pytest.raises(ValueError, match="Every accepted assertion"):
        plan_from_proposal(proposal, facts, evidence, *scope)


def test_structured_review_cannot_override_modality_negation_or_caption_failure():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    assessment = PlanAssessment.model_validate(
        {
            "clauses": [
                {
                    "development_key": d.key,
                    "clause_index": 0,
                    "conclusion": "supported",
                    "source_modality": d.clauses[0].modality,
                    "source_negated": False,
                    "issues": [],
                    "reason": "Owned literal support",
                }
                for d in plan.developments
            ],
            "anchors": [{"evidence_id": e.id, "role": "action"} for e in evidence],
            "structural_issues": [],
            "omitted_context": [],
        }
    )
    valid = assess_plan(plan, assessment)
    assert valid.factual.status == valid.structural.status == "passed"
    assessment.clauses[1].source_modality = "completed"
    assessment.clauses[0].source_negated = True
    assessment.anchors[0].role = "caption"
    invalid = assess_plan(plan, assessment)
    assert invalid.factual.status == invalid.structural.status == "blocked"
    assert "Inconsistent reviewer" in " ".join(invalid.factual.issues)
    assert plan.structural.status == "pending"  # Original artifact was not mutated.


@pytest.mark.asyncio
async def test_missing_archive_context_blocks_composition_and_reuses_diagnostics():
    from .test_arc_intelligence import arc_fixture, inference

    class MissingEvidence:
        async def development_evidence(self, *args):
            return [], ["missing_or_ineligible_archived_evidence"]

    service, universe, continuity, arc, _, _ = arc_fixture()
    service.evidence = MissingEvidence()
    calls = []
    for _ in range(2):
        result = await service.rebuild(
            universe, continuity, arc, 7, inference(calls), lambda: [], section_keys=["entry"]
        )
        assert result["article"]["status"] == "withheld"
        assert result["dossier"]["sections"][0]["coverage"]["research"] == "blocked"
    assert calls == ["planning"]


@pytest.mark.asyncio
async def test_fixed_reference_evidence_fails_closed_on_scope_or_budget():
    from src.application.controlled_narrative import FixedDevelopmentEvidence

    _, facts, units, _, _, continuity = material()
    universe = uuid4()
    evidence = FixedDevelopmentEvidence(universe, continuity, units)
    assert (await evidence.development_evidence(universe, continuity, facts, 2))[0] == units
    for wrong_continuity, ceiling, budget in [
        (uuid4(), 2, 3200),
        (continuity, 1, 3200),
        (continuity, 2, 1),
    ]:
        passages, issues = await evidence.development_evidence(
            universe, wrong_continuity, facts, ceiling, budget
        )
        assert not passages and issues
