"""Owned deterministic controls, not evidence of real research quality."""

import json
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.application.arc_contracts import ArcSectionDraft, DevelopmentEvidence, DevelopmentOrdering
from src.application.arc_grounding import CALIBRATION, copied_paragraphs, review_ok
from src.application.arc_prose import (
    ROLE_CALIBRATION,
    PlainScene,
    Propositions,
    ProseDraft,
    SceneAlignment,
    SceneDraft,
    aligned_scene,
    assess_in_batches,
    assess_written_section,
    bind_draft,
    bind_writing_notes,
    clarify_note_roles,
    flatten_scenes,
    originality_candidates,
    revision_note_targets,
    scene_inputs,
    validate_propositions,
    validate_scene_alignment_order,
    verify_link_use,
    writing_packet,
)
from src.application.arc_reconstruction import (
    FrameCandidates,
    FrameDecisions,
    Reconstruction,
    SceneState,
    bind_frames,
    reconstruct_arc,
)
from src.application.development_plan import (
    DevelopmentBatchReview,
    PlanAssessment,
    PlanProposal,
    RelationshipCandidate,
    anchored_relationship,
    assess_plan,
    clause_map,
    explicit_chronology,
    fence_repeated_anchors,
    layers,
    plan_from_proposal,
    reconstruct_relationships,
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


async def test_frame_review_holds_wrong_owner_and_retains_supported_speaker_role():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    scene, clause = next(iter(clause_map(plan).values()))
    clause.clause = "Shanks revealed that Luffy's body was now made of rubber."
    clause.modality = "completed"
    unit = next(u for u in plan.evidence if u.id == clause.evidence_ids[0])
    unit.text = clause.clause

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        if schema is FrameCandidates:
            ref = next(iter(packet))
            return (
                schema.model_validate(
                    {
                        "frames": [
                            {
                                "clause": ref,
                                "action": "developed rubber properties",
                                "speaker": "Shanks",
                                "experiencer": name,
                                "modality": "completed",
                                "negated": False,
                                "function": "turning_point",
                            }
                            for name in ("Luffy", "Shanks")
                        ]
                    }
                )
                if ref == "1.1"
                else schema.model_validate({"frames": []})
            )
        assert schema is FrameDecisions
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": id,
                        "supported": id in {"1", "2", "4"},
                        "reason": "Exact ownership checked",
                        "observed_modality": "completed" if id in {"1", "2"} else None,
                        "observed_roles": (
                            {"speaker": "Shanks", "experiencer": "Luffy"}
                            if id in {"1", "2"}
                            else {}
                        ),
                    }
                    for id in packet
                ]
            }
        )

    async def checkpoint() -> None:
        pass

    reconstruction = await reconstruct_arc(plan, facts, infer, {}, checkpoint)
    verified = next(s for s in reconstruction.scenes if s.id == scene.id).frames
    assert len(verified) == 1
    assert verified[0].roles["speaker"].name == "Shanks"
    assert verified[0].roles["experiencer"].name == "Luffy"
    assert not reconstruction.ready


def test_aligned_prose_cannot_reverse_a_verified_sequence_within_a_scene():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    scene, other = plan.developments
    scene.clauses.extend(other.clauses)
    plan.developments = [scene]
    refs = clause_map(plan)
    before, after = refs
    frames = bind_frames(
        FrameCandidates.model_validate(
            {
                "frames": [
                    {
                        "clause": ref,
                        "actor": clause.clause.split()[0],
                        "action": "open the gate",
                        "modality": clause.modality,
                        "negated": False,
                        "function": "action",
                    }
                    for ref, (_, clause) in refs.items()
                ]
            }
        ),
        plan,
        scene.id,
        {ref: [] for ref in refs},
        facts,
    )
    state = Reconstruction(scenes=[SceneState(id=scene.id, title=scene.title, frames=frames)])
    plan.relationship_review.status = "passed"
    plan.ordering.append(
        DevelopmentOrdering(
            before=scene.id,
            after=scene.id,
            before_clause=before,
            after_clause=after,
            kind="narrative_presentation",
            statement="The source gives an explicit transition.",
            evidence_ids=[e.id for e in evidence],
        )
    )
    draft = ArcSectionDraft.model_validate(
        {
            "heading": "Gate",
            "paragraphs": [
                {
                    "claims": [
                        {
                            "text": clause.clause,
                            "fact_ids": [clause.fact_id],
                            "writing_note_ids": [str(i)],
                        }
                        for i, (_, clause) in enumerate(refs.values(), 1)
                    ]
                }
            ],
        }
    )
    validate_scene_alignment_order(draft, state, plan)
    draft.paragraphs[0].claims.reverse()
    with pytest.raises(ValueError, match="reverses an evidenced action sequence"):
        validate_scene_alignment_order(draft, state, plan)


def test_attempt_cannot_be_completed_without_an_independent_exact_action():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    key, (scene, _) = next(
        (k, value) for k, value in clause_map(plan).items() if value[1].modality == "attempted"
    )
    frames = FrameCandidates.model_validate(
        {
            "frames": [
                {
                    "clause": key,
                    "actor": "Mira",
                    "action": "opened the gate",
                    "function": "resolution",
                    "modality": "completed",
                    "negated": False,
                }
            ]
        }
    )
    with pytest.raises(ValueError, match="non-completed"):
        bind_frames(frames, plan, scene.id, {key: []}, facts)


def test_alignment_cannot_omit_a_factual_sentence_or_rewrite_the_displayed_text():
    authored = PlainScene(paragraphs=["Mira reached the gate. Ron was inside."])
    alignment = SceneAlignment.model_validate(
        {
            "spans": [
                {"paragraph": 1, "start": 0, "end": 22, "frames": ["1"]},
                {"paragraph": 1, "start": 23, "end": 38, "frames": ["2"]},
            ]
        }
    )
    paragraphs = aligned_scene(authored, alignment, {"1", "2"})
    assert " ".join(c.text for c in paragraphs[0].claims) == authored.paragraphs[0]
    alignment.spans.pop()
    with pytest.raises(ValueError, match="left prose unaccounted"):
        aligned_scene(authored, alignment, {"1", "2"})


async def test_reconstruction_checks_links_within_compound_clauses_before_writing():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    clause = plan.developments[0].clauses[0]
    unit = next(u for u in plan.evidence if u.id in clause.evidence_ids)
    clause.clause = unit.text = "After Mira knocked, Ron opened the gate."
    candidate = {
        "before": "c1",
        "after": "c1",
        "before_excerpt": "Mira knocked",
        "after_excerpt": "Ron opened the gate",
        "evidence": [],
        "statement": "Ron opened the gate after Mira knocked.",
    }

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        payload = json.loads(prompt.split("\n", 1)[1])
        if task == "presentation":
            assert payload["actions"]["c1"]["text"] == clause.clause
            return schema.model_validate(
                {
                    "links": [
                        {**candidate, "kind": "chronology"},
                        {
                            **candidate,
                            "kind": "causal",
                            "statement": "The knock caused the gate to open.",
                        },
                        {**candidate, "kind": "chronology", "before_excerpt": "Mira fell"},
                    ],
                    "gaps": [],
                }
            )
        assert payload["r1"]["archive"] == [unit.text]
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": "r1",
                        "verdict": "supported",
                        "reason": "Explicit after clause.",
                        "observed_kind": "chronology",
                    },
                    {"id": "r2", "verdict": "unsupported", "reason": "Only an order is stated."},
                    {
                        "id": "control",
                        "verdict": "unsupported",
                        "reason": "Only an order is stated.",
                    },
                ]
            }
        )

    updated = await reconstruct_relationships(plan, infer)
    assert updated.relationship_review.status == "passed"
    links = [o for o in updated.ordering if o.statement]
    assert [link.kind for link in links] == ["chronology"]
    assert links[0].before == links[0].after == plan.developments[0].id
    assert links[0].evidence_ids == [unit.id]
    assert any("not bound" in issue for issue in updated.relationship_review.issues)
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": "1.1",
                    "actor": "Mira",
                    "action": "knocked",
                    "target": "gate",
                    "modality": "completed",
                    "negated": False,
                    "purpose_or_limit": "",
                }
            ]
        }
    )
    links_in_packet = writing_packet(updated, notes)["supported_links"]
    assert isinstance(links_in_packet, list)
    assert len(links_in_packet) == 1 and links_in_packet[0]["kind"] == "chronology"
    bound = bind_writing_notes(
        ProseDraft.model_validate(
            {
                "paragraphs": [
                    {
                        "claims": [
                            {
                                "text": "Ron opened the gate after Mira knocked.",
                                "clauses": ["1"],
                                "relations": [links_in_packet[0]["id"]],
                            }
                        ]
                    }
                ]
            }
        ),
        updated,
        notes,
        "Gate",
    )
    claim = bound.paragraphs[0].claims[0]
    assert claim.context_evidence_ids == [unit.id]
    assert claim.relationship_ids == [links_in_packet[0]["id"]]
    claim.text = "Ron opened the gate before Mira knocked."

    async def review_usage(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        link_id = links_in_packet[0]["id"]
        assert packet[link_id]["authored_passages"] == [claim.text]
        return schema.model_validate(
            {
                "decisions": [
                    {"id": key, "verdict": "reversed", "reason": "The prose reverses the order"}
                    for key in packet
                ]
            }
        )

    async def checkpoint() -> None:
        pass

    issues, missing, repair = await verify_link_use(
        bound, updated, notes, review_usage, {}, checkpoint
    )
    assert issues and "reversed" in issues[0]
    assert not missing and repair == {1}


def test_chronology_cannot_borrow_a_later_cue_across_intervening_evidence():
    _, _, evidence, *_ = material()
    before, after = evidence
    after.text = "Then Ron opened the gate."
    intervening = before.model_copy(update={"start": before.end + 1, "id": "intervening"})
    assert explicit_chronology("Mira tried", "Ron opened", evidence, evidence)
    assert not explicit_chronology(
        "Mira tried", "Ron opened", evidence, [before, intervening, after]
    )


def test_parallel_endpoint_binds_exact_words_to_a_licensed_action():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    first, second = list(clause_map(plan))
    first_clause = clause_map(plan)[first][1]
    alternate = evidence[0].model_copy(
        update={
            "id": "parallel",
            "source_id": uuid4(),
            "text": "Mira attempted to raise the gate.",
        }
    )
    plan.evidence.append(alternate)
    other = clause_map(plan)[second][1]
    candidate = RelationshipCandidate(
        before=first,
        after=second,
        before_excerpt=alternate.text,
        after_excerpt=other.clause,
        kind="resolution",
        evidence=["e3"],
        statement="Ron opened the gate after Mira attempted it.",
    )
    link = anchored_relationship(candidate, plan, plan.evidence)
    assert alternate.id in link.evidence_ids
    assert first_clause.fact_id in link.fact_ids
    candidate.evidence = []
    if alternate.text != first_clause.clause:
        with pytest.raises(ValueError, match="not bound"):
            anchored_relationship(candidate, plan, plan.evidence)


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
    verdicts = ["unsupported"]

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        assert task == "presentation_verification"
        packet = json.loads(prompt.split("\n", 1)[1])
        assert packet["evidence"] == {attempt: evidence[0].text}
        return schema.model_validate(
            {
                "rejected": rejected,
                "verdicts": verdicts,
                "originality_issues": [],
                "editorial_issues": [],
            }
        )

    assessment = await assess_written_section(draft, plan, reviewer)
    assert assessment.claims[0].verdict == "unsupported"
    verdicts[0] = "supported"
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


async def test_archive_context_is_cited_without_exposing_it_to_the_writer():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    first, second = list(clause_map(plan))
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": first,
                    "actor": "Mira",
                    "action": "try",
                    "target": "gate",
                    "modality": "attempted",
                    "negated": False,
                    "purpose_or_limit": "",
                    "context": ["e2"],
                    "essential": True,
                },
                {
                    "id": second,
                    "actor": "Ron",
                    "action": "open",
                    "target": "gate",
                    "modality": "completed",
                    "negated": False,
                    "purpose_or_limit": "",
                    "essential": True,
                },
            ],
        }
    )
    validate_propositions(plan, notes)
    packet = json.dumps(writing_packet(plan, notes))
    assert all(unit.text not in packet for unit in evidence)
    draft = bind_writing_notes(
        ProseDraft.model_validate(
            {
                "paragraphs": [
                    {"claims": [{"text": "Mira attempted to open the gate.", "clauses": ["1"]}]},
                ]
            }
        ),
        plan,
        notes,
        "Gate",
    )
    assert draft.paragraphs[0].claims[0].context_evidence_ids == [evidence[1].id]

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        payload = json.loads(prompt.split("\n", 1)[1])
        assert payload["context"] == {"1": evidence[1].text}
        return schema.model_validate(
            {
                "verdicts": ["supported"],
                "rejected": [],
                "editorial_issues": [],
                "originality_issues": ["Close rephrasing"],
                "revise_paragraphs": [1],
            }
        )

    result = await assess_written_section(draft, plan, reviewer, notes)
    assert "Missing essential writing notes: 2" in result.coverage_issues
    assert result.revision_paragraphs == [1]
    assert revision_note_targets(draft, plan, notes) == {1: {"1"}}


async def test_planned_review_requires_the_same_response_to_pass_role_calibration():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref = next(iter(clause_map(plan)))
    draft = bind_draft(
        ProseDraft.model_validate(
            {
                "paragraphs": [
                    {
                        "claims": [
                            {
                                "text": "Mira walked around the gate.",
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
    calibration = [c["expected"] for c in [*CALIBRATION, *ROLE_CALIBRATION]]
    calibration[len(CALIBRATION)] = True  # Rescue and drive share the wrong object.

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        cases = json.loads(prompt.split("\n", 1)[1])["calibration"]
        assert cases[len(CALIBRATION)]["text"] == "Mira rescued and drove away the wolf."
        assert "grammatical subject and object" in prompt
        return schema.model_validate(
            {
                "verdicts": ["unsupported"],
                "rejected": [{"index": 0, "kind": "unsupported", "reason": "Wrong action."}],
                "editorial_issues": [],
                "originality_issues": [],
                "calibration": calibration,
            }
        )

    review = await assess_written_section(draft, plan, reviewer, calibrate=True)
    assert review.qualification_passed is False
    assert not review_ok(review, 1)


async def test_batched_grounding_resumes_without_repeating_completed_sentences():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    refs = list(clause_map(plan))
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": ref,
                    "actor": "Mira",
                    "action": "try",
                    "target": "gate",
                    "modality": "attempted",
                    "negated": False,
                    "purpose_or_limit": "",
                }
                for ref in refs
            ]
        }
    )
    draft = bind_writing_notes(
        ProseDraft.model_validate(
            {
                "paragraphs": [
                    {"claims": [{"text": "The gate stayed closed.", "clauses": ["1"]}]},
                    {"claims": [{"text": "Mira tried to open it.", "clauses": ["2"]}]},
                ]
            }
        ),
        plan,
        notes,
        "Gate",
    )
    cache: dict[str, dict[str, object]] = {}
    calls: list[str] = []
    checkpoints: list[int] = []

    async def checkpoint() -> None:
        checkpoints.append(len(cache))

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        if "paragraphs" in packet:
            return schema.model_validate(
                {
                    "editorial_issues": [],
                    "originality_issues": [],
                    "coverage_issues": [],
                    "revise_paragraphs": [],
                }
            )
        sentence = packet["s1"]["sentence"]
        calls.append(sentence)
        decisions = [
            {
                "id": i,
                "verdict": "unsupported" if i in {"check-a", "check-c", "check-d"} else "supported",
                "reason": "Evidence checked",
            }
            for i in packet
        ]
        if len(calls) == 2:
            decisions.pop()
        return schema.model_validate({"decisions": decisions})

    with pytest.raises(ValueError, match="incomplete or duplicate"):
        await assess_in_batches(draft, plan, notes, reviewer, cache, checkpoint)
    assert checkpoints == [1]
    result = await assess_in_batches(draft, plan, notes, reviewer, cache, checkpoint)
    assert result.qualification_passed
    assert calls == ["The gate stayed closed.", "Mira tried to open it.", "Mira tried to open it."]
    assert checkpoints == [1, 2, 3]

    for key, value in list(cache.items()):
        if "editorial_issues" in value:
            del cache[key]

    async def malformed_editor(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        assert "paragraphs" in packet  # Factual batches are still reusable.
        return schema.model_validate(
            {
                "editorial_issues": [],
                "originality_issues": ["A sentence is awkward."],
                "coverage_issues": [],
                "revise_paragraphs": [],
            }
        )

    result = await assess_in_batches(draft, plan, notes, malformed_editor, cache, checkpoint)
    assert result.qualification_passed
    assert not result.editorial_review_available
    assert not result.originality_issues
    assert not review_ok(result, 2)


def test_scene_checkpoint_depends_on_neighbor_relationships_and_notes():
    packet = {
        "developments": [
            {"id": f"scene-{i}", "notes": [{"actor": "Mira", "action": str(i), "essential": True}]}
            for i in range(1, 4)
        ],
        "reference_order_layers": [["scene-1"], ["scene-2"], ["scene-3"]],
        "supported_links": [
            {"before": "scene-1", "after": "scene-1", "connection": "A then B"},
        ],
    }
    before = {i: key for i, key, _ in scene_inputs(packet)}
    packet["supported_links"][0]["connection"] = "A precedes C"
    after = {i: key for i, key, _ in scene_inputs(packet)}
    assert {i for i in before if before[i] != after[i]} == {"scene-1", "scene-2"}
    packet["developments"][1]["notes"][0]["action"] = "changed note"
    changed = {i: key for i, key, _ in scene_inputs(packet)}
    assert all(changed[i] != after[i] for i in after)


async def test_scene_review_preserves_context_and_rejects_unknown_archive_anchor():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref, (_, clause) = next(iter(clause_map(plan).items()))
    direct = next(u for u in plan.evidence if u.id in clause.evidence_ids)
    direct.text = "Ada held a lantern at the bridge."
    clause.clause = direct.text
    plan.evidence.append(
        direct.model_copy(
            update={
                "id": "corroboration",
                "text": "At the bridge Ada raised the lantern.",
            }
        )
    )
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": ref,
                    "actor": "Ada",
                    "action": "held",
                    "target": "lantern",
                    "modality": "completed",
                    "negated": False,
                    "purpose_or_limit": "",
                }
            ]
        }
    )
    draft = bind_writing_notes(
        ProseDraft.model_validate(
            {
                "paragraphs": [
                    {
                        "claims": [
                            {"text": "Ada was at the bridge.", "clauses": ["1"]},
                            {"text": "She held the lantern at the bridge.", "clauses": ["1"]},
                        ]
                    }
                ]
            }
        ),
        plan,
        notes,
        "Bridge",
    )

    async def checkpoint() -> None:
        pytest.fail("An invalid archive anchor must not be saved")

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        assert packet["s2"]["nearby_prose"] == ["Ada was at the bridge."]
        assert packet["s2"]["archive_alternatives"] == {
            "a1": "At the bridge Ada raised the lantern."
        }
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": key,
                        "verdict": "supported",
                        "reason": "Accepted",
                        "anchors": ["made-up-id"] if key == "s2" else [],
                    }
                    for key in packet
                ]
            }
        )

    with pytest.raises(ValueError, match="unavailable archive anchor"):
        await assess_in_batches(draft, plan, notes, infer, {}, checkpoint)


def test_scene_prose_keeps_reader_paragraphs_and_rejects_foreign_citations():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    refs = list(clause_map(plan))
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": ref,
                    "actor": "Mira",
                    "action": "try",
                    "target": "gate",
                    "modality": "attempted",
                    "negated": False,
                    "purpose_or_limit": "",
                }
                for ref in refs
            ]
        }
    )
    scenes = SceneDraft.model_validate(
        {
            "scenes": [
                {
                    "id": f"scene-{i}",
                    "paragraphs": [
                        {
                            "claims": [
                                {
                                    "text": "Mira tried the gate. Her attempt failed.",
                                    "clauses": [str(i)],
                                }
                            ]
                        }
                    ],
                }
                for i in (1, 2)
            ]
        }
    )
    # Preserve the actual sentence grouping. Grounding decides whether both sentences follow.
    draft = flatten_scenes(scenes, plan, notes)
    assert len(draft.paragraphs) == 2
    assert draft.paragraphs[0].claims[0].text == "Mira tried the gate. Her attempt failed."
    scenes.scenes[0].paragraphs[0].claims[0].clauses = ["2"]
    with pytest.raises(ValueError, match="outside its development"):
        flatten_scenes(scenes, plan, notes)
    scenes.scenes.pop()
    with pytest.raises(ValueError, match="each planned scene once"):
        flatten_scenes(scenes, plan, notes)


async def test_role_correction_uses_the_explicit_cited_actor():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref, (_, clause) = next(iter(clause_map(plan).items()))
    clause.clause = "Mira was saddened that she lost her glove during the rescue."
    statement = "Mira was sad that Ada lost a glove while rescuing her."
    plan.evidence.append(
        evidence[0].model_copy(
            update={
                "id": "3",
                "source_id": uuid4(),
                "text": statement,
            }
        )
    )
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": ref,
                    "actor": "Mira",
                    "action": "lost",
                    "target": "glove",
                    "modality": "completed",
                    "negated": False,
                    "purpose_or_limit": "",
                    "context": ["e3"],
                }
            ]
        }
    )

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        assert packet["1"]["explicit_context"] == [statement]
        return schema.model_validate(
            {
                "fixes": [
                    {"note": 1, "actor": "Ada", "action": "lost", "target": "glove"},
                ]
            }
        )

    fixed = await clarify_note_roles(plan, notes, infer)
    assert fixed.notes[0].actor == "Ada"
    assert fixed.notes[0].context == ["e3"]
    assert fixed.notes[0].modality == "completed"


def test_source_phrasing_is_rejected_before_writing():
    proposal, facts, evidence, *scope = material()
    evidence[0].text = "Behind the rusted gate Mira waited for Ron to return with the iron key."
    evidence[0].end = evidence[0].start + len(evidence[0].text)
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    notes = Propositions.model_validate(
        {
            "notes": [
                {
                    "id": next(iter(clause_map(plan))),
                    "actor": "Mira",
                    "action": evidence[0].text,
                    "target": "",
                    "modality": "completed",
                    "negated": False,
                    "purpose_or_limit": "",
                }
            ],
        }
    )
    with pytest.raises(ValueError, match="repeat archived source wording"):
        validate_propositions(plan, notes)


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
