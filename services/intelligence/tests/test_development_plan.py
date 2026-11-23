"""Owned deterministic controls, not evidence of real research quality."""

import json
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.application.arc_contracts import ArcSectionDraft, DevelopmentEvidence
from src.application.arc_grounding import copied_paragraphs
from src.application.arc_prose import (
    Propositions,
    ProseDraft,
    assess_written_section,
    bind_draft,
    originality_candidates,
    validate_propositions,
    writing_packet,
)
from src.application.development_plan import (
    DevelopmentBatchReview,
    PlanAssessment,
    PlanProposal,
    assess_plan,
    clause_map,
    fence_repeated_anchors,
    layers,
    plan_from_proposal,
    review_developments,
)
from src.application.research_contracts import Task


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


def test_prose_packet_is_source_isolated_and_only_binds_licensed_notes():
    proposal, facts, evidence, *scope = material()
    for item in proposal.developments:
        item.title = item.key
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    attempt = next(key for key, (_, claim) in clause_map(plan).items() if claim.fact_id == "f0")
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": attempt,
                    "actor": "Mira",
                    "action": "open",
                    "target": "gate",
                    "modality": "attempted",
                    "negated": False,
                    "purpose_or_limit": "",
                }
            ],
        }
    )
    validate_propositions(plan, notes)
    assert evidence[0].text not in json.dumps(writing_packet(plan, notes))
    draft = ProseDraft.model_validate(
        {
            "paragraphs": [
                {"claims": [{"text": "Mira attempted to get the gate open.", "clauses": [attempt]}]}
            ],
        }
    )
    assert bind_draft(draft, plan, {attempt}, "Gate").paragraphs[0].fact_ids == ["f0"]
    with pytest.raises(ValueError, match="outside the licensed"):
        bind_draft(draft, plan, set(), "Gate")
    notes.notes[0].id = "90.1"
    with pytest.raises(ValueError, match="unknown scoped clause"):
        validate_propositions(plan, notes)


@pytest.mark.asyncio
async def test_planned_prose_review_binds_original_wording_and_rejects_incomplete_verdicts():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    attempt = next(key for key, (_, claim) in clause_map(plan).items() if claim.fact_id == "f0")
    raw = ProseDraft.model_validate(
        {
            "paragraphs": [
                {
                    "claims": [
                        {
                            "text": "Mira opened the gate to prove her courage.",
                            "clauses": [attempt],
                        },
                    ]
                }
            ],
        }
    )
    draft = bind_draft(raw, plan, {attempt}, "Gate")
    rejected = [
        {
            "index": 0,
            "kind": "unsupported",
            "reason": "The evidence supports an attempt and establishes no motive.",
        }
    ]
    supported: list[int] = []

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        assert task == "presentation_verification"
        packet = json.loads(prompt.split("\n", 1)[1])
        assert packet["evidence"] == {attempt: evidence[0].text}
        return schema.model_validate(
            {
                "rejected": rejected,
                "supported": supported,
                "originality_issues": [],
                "editorial_issues": [],
            }
        )

    assessment = await assess_written_section(draft, plan, reviewer)
    assert assessment.claims[0].verdict == "unsupported"
    supported.append(0)
    with pytest.raises(ValueError, match="contradictory"):
        await assess_written_section(draft, plan, reviewer)


def test_near_verbatim_prose_is_flagged_for_review():
    proposal, facts, evidence, *scope = material()
    original = "Behind the rusted gate Mira waited for Ron to return with the old iron key."
    evidence[0].text = original
    evidence[0].end = evidence[0].start + len(original)
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref = next(iter(clause_map(plan)))
    draft = bind_draft(
        ProseDraft.model_validate(
            {
                "paragraphs": [
                    {
                        "claims": [
                            {
                                "text": (
                                    "Behind the rusted gate Mira waited for Ron "
                                    "to come back with the iron key."
                                ),
                                "clauses": [ref],
                            }
                        ]
                    }
                ]
            }
        ),
        plan,
        {ref},
        "Gate",
    )
    assert originality_candidates(draft, plan) == [{"paragraph": 1, "unit": "1"}]
    assert copied_paragraphs(draft, plan) == []


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
async def test_review_replaces_caption_anchor_and_withholds_conflicting_development():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    first, second = plan.developments
    first.clauses += second.clauses
    original_anchor = first.anchor_ids[:]

    async def infer(prompt, schema, task):
        assert schema is DevelopmentBatchReview
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "development": 1,
                        "supported": [2],
                        "rejected": [1],
                        "anchor": 2,
                        "issues": ["First reference is a caption"],
                    },
                    {
                        "development": 2,
                        "supported": [1],
                        "rejected": [1],
                        "anchor": 1,
                        "issues": ["Contradictory review"],
                    },
                ]
            }
        )

    result = await review_developments(plan, infer, facts)
    assert result.structural.status == result.factual.status == "passed"
    assert len(result.developments) == 1
    assert result.developments[0].anchor_ids == second.anchor_ids
    assert first.anchor_ids == original_anchor
    assert any("contradictory" in gap for gap in result.gaps)
    assert len(result.evidence) == len(plan.evidence)


def test_repeated_source_label_cannot_anchor_a_reviewed_development():
    proposal, facts, evidence, *scope = material()
    repeated = evidence[0].model_copy(update={"id": "repeat"})
    repeated.start = evidence[0].end + 1
    repeated.end = repeated.start + len(repeated.text)
    plan = plan_from_proposal(proposal, facts, [*evidence, repeated], *scope)
    anchored = next(d for d in plan.developments if d.anchor_ids == [evidence[0].id])
    fallback = next(d for d in plan.developments if d.id != anchored.id)
    anchored.clauses.extend(fallback.clauses)
    plan.developments = [anchored]
    repaired = fence_repeated_anchors(plan)
    assert repaired.developments[0].anchor_ids == fallback.anchor_ids
    assert repaired.developments[0].id == anchored.id
    assert anchored.anchor_ids == [evidence[0].id]
    assert repaired.evidence == plan.evidence


def test_originality_check_flags_only_long_verbatim_paragraphs():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    source = (
        "After the afternoon storm passed over the harbor the crew returned to the dock to "
        "inspect the damaged ropes before the next departure."
    )
    plan.evidence[0].text = source
    draft = ArcSectionDraft.model_validate(
        {
            "heading": "Owned fixture",
            "paragraphs": [
                {"claims": [{"text": source, "fact_ids": ["a"]}]},
                {
                    "claims": [
                        {
                            "text": "The crew checked the ropes when the storm had passed.",
                            "fact_ids": ["a"],
                        }
                    ]
                },
            ],
        }
    )
    assert copied_paragraphs(draft, plan) == [1]


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
