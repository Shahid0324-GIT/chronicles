"""Owned deterministic controls, not evidence of real research quality."""

import json
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.application import arc_prose
from src.application.arc_contracts import ArcSectionDraft, DevelopmentEvidence, DevelopmentOrdering
from src.application.arc_grounding import copied_paragraphs, review_ok
from src.application.arc_prose import (
    ROLE_CALIBRATION,
    FrameCitation,
    FrameCitations,
    PlainScene,
    Propositions,
    ProseDraft,
    SceneAlignment,
    aligned_scene,
    assess_in_batches,
    bind_draft,
    bind_writing_notes,
    clarify_note_roles,
    compose_reconstruction,
    composition_requirements,
    frame_citations,
    grounding_rows,
    originality_candidates,
    revision_note_targets,
    validate_propositions,
    validate_scene_alignment_order,
    verify_link_use,
    write_and_align,
    writing_packet,
)
from src.application.arc_reconstruction import (
    FrameCandidates,
    FrameDecision,
    FrameDecisions,
    Reconstruction,
    SceneState,
    apply_frame_decision,
    bind_frames,
    incomplete_review,
    qualify_frames,
    reconstruct_arc,
    valid_decision,
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
from src.application.research_contracts import InferenceFailure, Task


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
    plan.developments.reverse()  # The fixture supplies developments in reverse source order.
    scene, clause = next(iter(clause_map(plan).values()))
    clause.clause = "Shanks revealed that Luffy's body was now made of rubber."
    clause.modality = "completed"
    unit = next(u for u in plan.evidence if u.id == clause.evidence_ids[0])
    unit.text = clause.clause
    review_batches = []

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        if schema is FrameCandidates:
            ref = next(iter(packet))
            assert packet[ref]["direct"]
            assert packet[ref]["context"]
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
                else schema.model_validate(
                    {
                        "frames": [
                            {
                                "clause": ref,
                                "action": "opened the gate",
                                "actor": "Ron",
                                "modality": "completed",
                                "negated": False,
                                "function": "action",
                            }
                        ]
                    }
                )
            )
        if schema is PlainScene:
            assert len(packet["scenes"]) == 2
            assert [scene["frames"] for scene in packet["scenes"]] == [["1"], ["2"]]
            frame = packet["frames"]["1"]
            assert frame["roles"]["speaker"]["name"] == "Shanks"
            assert frame["roles"]["experiencer"]["name"] == "Luffy"
            return PlainScene(paragraphs=["Luffy had changed. Ron opened it."])
        if schema is SceneAlignment:
            assert list(packet["spans"]) == ["1", "2"]
            return schema.model_validate(
                {
                    "spans": [
                        {"span": 1, "frames": ["1"]},
                        {"span": 2, "frames": ["2"]},
                    ]
                }
            )
        assert schema is FrameDecisions
        proposed = [v["proposition"] for v in packet.values()]
        review_batches.append(proposed)
        return schema.model_validate(
            {
                "decisions": {
                    key: {"supported": False, "reason": "The change belongs to Luffy."}
                    if v["proposition"]["participants"].get("experiencer") == "Shanks"
                    else {
                        "supported": True,
                        "witness": v["evidence_id"]["e1"],
                        "reason": "The subject and action match the archive.",
                        "observed_modality": "completed",
                    }
                    for key, v in packet.items()
                }
            }
        )

    async def checkpoint() -> None:
        pass

    reconstruction = await reconstruct_arc(plan, facts, infer, {}, checkpoint)
    verified = next(s for s in reconstruction.scenes if s.id == scene.id).frames
    assert len(verified) == 1
    assert verified[0].roles["speaker"].name == "Shanks"
    assert verified[0].roles["experiencer"].name == "Luffy"
    assert reconstruction.ready
    assert any("belongs to Luffy" in gap for gap in reconstruction.scenes[0].gaps)
    assert [len(batch) for batch in review_batches] == [2, 1]
    notes = frame_citations(reconstruction, plan)
    cache = {}
    assert composition_requirements(reconstruction, plan, notes, cache, "Change") == (1, 5)
    draft = await compose_reconstruction(
        reconstruction, plan, notes, "Change", infer, cache, checkpoint
    )
    assert composition_requirements(reconstruction, plan, notes, cache, "Change") == (0, 2)
    assert [p.text for p in draft.paragraphs] == ["Luffy had changed. Ron opened it."]
    assert [claim.writing_note_ids for claim in draft.paragraphs[0].claims] == [["1"], ["2"]]


async def test_alignment_retries_only_invalid_rows():
    original = "Mira asked to join the group. Ron led the group to town."
    context = {
        "frames": {
            "1": {"action": "Mira asked to join the group."},
            "2": {"action": "Ron led the group to town."},
        },
        "essential_frames": ["1"],
        "relationships": {},
    }
    alignment_calls: list[list[str]] = []

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        payload = json.loads(prompt.rsplit("\n", 1)[1])
        if schema is PlainScene:
            return PlainScene(paragraphs=[original])
        assert schema is SceneAlignment
        alignment_calls.append(list(payload["spans"]))
        if len(alignment_calls) == 1:
            return schema.model_validate(
                {
                    "spans": [
                        {"span": 1, "frames": ["1"]},
                        {"span": 2, "frames": "foreign"},
                    ]
                }
            )
        if len(alignment_calls) == 2:
            return schema.model_validate({"spans": [{"span": 2, "frames": ["99"]}]})
        return schema.model_validate({"spans": [{"span": 2, "frames": ["2"]}]})

    async def checkpoint() -> None:
        pass

    diagnostics = {}
    cache = {}
    with pytest.raises(ValueError, match="Alignment incomplete for spans 2"):
        await write_and_align(context, infer, cache, checkpoint, diagnostics=diagnostics)
    assert diagnostics["alignment"] == {"mapped": 1, "unmapped_span_ids": [2]}

    paragraphs, _ = await write_and_align(
        context, infer, cache, checkpoint, diagnostics=diagnostics
    )
    assert " ".join(c.text for c in paragraphs[0].claims) == original
    assert alignment_calls == [["1", "2"], ["2"], ["2"]]
    await write_and_align(context, infer, cache, checkpoint)
    assert len(alignment_calls) == 3


async def test_alignment_reuses_sentences_outside_an_edited_neighborhood():
    original = ["Mira asked to join. Ron waved. The group left. Mira stayed behind."]
    revised = ["Mira asked to join.", "Ron waved. The group left. Mira waited by the gate."]
    calls = []
    context = {
        "frames": {"1": {"action": "Qualified fixture action."}},
        "essential_frames": ["1"],
        "relationships": {},
    }

    async def infer(prompt, schema, task):
        packet = json.loads(prompt.split("\n", 1)[1])
        if schema is PlainScene:
            return PlainScene(paragraphs=revised if "grounded" in packet else original)
        calls.append(list(packet["spans"]))
        return schema.model_validate(
            {"spans": [{"span": int(ref), "frames": ["1"]} for ref in packet["spans"]]}
        )

    async def checkpoint():
        pass

    cache = {}
    await write_and_align(context, infer, cache, checkpoint)
    await write_and_align(context, infer, cache, checkpoint, edit={"draft": original})
    assert calls == [["1", "2", "3", "4"], ["3", "4"]]


async def test_alignment_keeps_late_sentence_coordinates_with_local_batch_ids():
    prose = " ".join(f"Mira describes matter {i}." for i in range(1, 8))
    context = {
        "frames": {str(i): {"action": f"Mira describes matter {i}."} for i in range(1, 8)},
        "essential_frames": [],
        "relationships": {},
    }
    calls = []

    async def infer(prompt, schema, task):
        payload = json.loads(prompt.rsplit("\n", 1)[1])
        if schema is PlainScene:
            return PlainScene(paragraphs=[prose])
        calls.append(list(payload["spans"]))
        return schema.model_validate(
            {
                "spans": [
                    {"span": int(local), "frames": [sentence.split()[-1].rstrip(".")]}
                    for local, sentence in payload["spans"].items()
                ]
            }
        )

    async def checkpoint():
        pass

    paragraphs, _ = await write_and_align(context, infer, {}, checkpoint)
    assert calls == [["1", "2", "3", "4", "5"], ["1", "2"]]
    assert [claim.clauses for claim in paragraphs[0].claims] == [[str(i)] for i in range(1, 8)]


async def test_empty_reconstruction_recovers_essential_actions_from_archive():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    recovered = []

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.rsplit("\n", 1)[1])
        if schema is FrameCandidates:
            if "Recover the indispensable meaning" not in prompt:
                return FrameCandidates(frames=[])
            ref, evidence_scope = next(iter(packet.items()))
            direct = next(iter(evidence_scope["direct"].values()))
            context = next(iter(evidence_scope["context"]))
            recovered.append((ref, direct["start"], direct["text"]))
            return schema.model_validate(
                {
                    "frames": [
                        {
                            "clause": next(iter(evidence_scope["direct"])).upper(),
                            "action": "open the gate",
                            "actor": direct["text"].split()[0],
                            "modality": "attempted" if "tried" in direct["text"] else "completed",
                            "negated": False,
                            "function": "action",
                            "context": [context.upper(), "unknown-id"],
                        }
                    ]
                }
            )
        [item] = packet.values()
        return schema.model_validate(
            {
                "decisions": {
                    "1": {
                        "supported": True,
                        "observed_negated": False,
                        "observed_modality": "attempted"
                        if "tried" in item["evidence_id"]["e1"]
                        else "completed",
                        "witness": item["evidence_id"]["e1"],
                        "reason": "The evidence supports the bound action and role.",
                    }
                }
            }
        )

    async def checkpoint() -> None:
        pass

    state = await reconstruct_arc(plan, facts, infer, {}, checkpoint)
    assert state.ready
    assert len(recovered) == 2
    assert all(scene.frames[0].roles["actor"].identity_id for scene in state.scenes)
    assert all(len(scene.frames[0].context) == 1 for scene in state.scenes)
    assert all(scene.frames[0].verified_witness for scene in state.scenes)


def test_state_can_qualify_without_forcing_an_actor_role():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref, (development, clause) = next(iter(clause_map(plan).items()))
    clause.modality = "completed"
    candidate = FrameCandidates.model_validate(
        {
            "frames": [
                {
                    "clause": ref,
                    "kind": "state",
                    "action": "The gate was open",
                    "modality": "completed",
                    "negated": False,
                    "function": "aftermath",
                }
            ]
        }
    )
    [frame] = bind_frames(candidate, plan, development.id, {ref: []}, facts)
    scene = SceneState(id=development.id, title=development.title)
    apply_frame_decision(
        frame, FrameDecision(supported=True, witness="Ron opened the gate."), scene
    )
    assert scene.frames[0].kind == "state" and not scene.frames[0].roles


async def test_pending_review_resumes_without_reextracting_or_rechecking_qualified_siblings():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    calls: list[str] = []
    cache = {}
    unavailable = True

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        request = json.loads(prompt.rsplit("\n", 1)[1])
        if schema is FrameCandidates:
            calls.append("extract")
            ref, item = next(iter(request.items()))
            return schema.model_validate(
                {
                    "frames": [
                        {
                            "clause": ref,
                            "action": item["statement"],
                            "modality": item["modality"],
                            "negated": False,
                            "function": "action",
                        }
                    ]
                }
            )
        [item] = request.values()
        action = item["proposition"]["meaning"]
        calls.append(action)
        if unavailable and "tried" in action:
            raise InferenceFailure("provider_unavailable")
        return schema.model_validate(
            {
                "decisions": {
                    "1": {
                        "supported": True,
                        "evidence_id": "e1",
                        "modality_confirmed": True,
                    }
                }
            }
        )

    async def checkpoint() -> None:
        pass

    first = await reconstruct_arc(plan, facts, infer, cache, checkpoint)
    blocked = next(s for s in first.scenes if not s.frames)
    assert blocked.pending_essential and not blocked.missing_essential
    assert next(iter(blocked.review_outcomes.values())).status == "provider_unavailable"
    unavailable = False
    calls.clear()
    second = await reconstruct_arc(plan, facts, infer, cache, checkpoint)
    assert second.ready and len(calls) == 1 and "tried" in calls[0]


async def test_recovery_can_correct_stale_negation_without_rewriting_the_plan():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    scene, clause = next(iter(clause_map(plan).values()))
    clause.negated = True

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.rsplit("\n", 1)[1])
        if schema is FrameCandidates:
            item = next(iter(packet.values()))
            text = next(iter(item["direct"].values()))["text"]
            return schema.model_validate(
                {
                    "frames": [
                        {
                            "clause": text,
                            "action": "open",
                            "excerpt": text,
                            "modality": "attempted" if "tried" in text else "completed",
                            "negated": False,
                            "function": "action",
                        }
                    ]
                }
            )
        return schema.model_validate(
            {
                "decisions": {
                    "1": {
                        "supported": True,
                        "evidence_id": "e1",
                        "modality_confirmed": True,
                    }
                }
            }
        )

    async def checkpoint() -> None:
        pass

    state = await reconstruct_arc(plan, facts, infer, {}, checkpoint)
    [corrected] = next(s for s in state.scenes if s.id == scene.id).frames
    assert corrected.revises_clause and not corrected.negated and clause.negated
    assert corrected.action == corrected.excerpt


async def test_saved_witness_only_approval_cannot_qualify_a_proposition():
    # This approval was returned by the first live semantic review of Origin.
    witness = (
        "After a year of them being there, a young boy named Monkey D. Luffy came to their ship "
        "to prove he was tough enough to join them by stabbing his face under his left eye."
    )
    saved_response = {
        "decisions": {
            "1": {
                "supported": True,
                "reason": "",
                "observed_modality": None,
                "observed_negated": None,
                "observed_roles": {},
                "witness": witness,
            }
        }
    }
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref, (development, clause) = next(iter(clause_map(plan).items()))
    clause.modality = "completed"
    unit = next(unit for unit in plan.evidence if unit.id in clause.evidence_ids)
    unit.text = witness
    candidate = FrameCandidates.model_validate(
        {
            "frames": [
                {
                    "clause": ref,
                    "action": "Luffy stabbed his left eye",
                    "actor": "Luffy",
                    "modality": "completed",
                    "negated": False,
                    "function": "action",
                }
            ]
        }
    )
    [frame] = bind_frames(candidate, plan, development.id, {ref: []}, facts)
    scene = SceneState(id=development.id, title=development.title)

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        return schema.model_validate(saved_response)

    async def checkpoint() -> None:
        pytest.fail("An incomplete approval must not enter the verified cache")

    assert await qualify_frames(
        [frame], {unit.id: unit}, {unit.id: []}, infer, {}, checkpoint, scene
    ) == [frame]
    assert not scene.frames and not scene.gaps
    assert scene.review_outcomes[frame.id].status == "missing_modality"
    assert incomplete_review(frame, None, {unit.id: unit}) == "incomplete_response"
    assert (
        incomplete_review(
            frame, FrameDecision(supported=True, modality_confirmed=True), {unit.id: unit}
        )
        == "missing_witness"
    )
    assert (
        incomplete_review(frame, FrameDecision(supported=True, evidence_id="e99"), {unit.id: unit})
        == "invalid_witness"
    )


def test_completed_report_cannot_certify_reported_action_as_actual():
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    ref, (development, clause) = next(iter(clause_map(plan).items()))
    clause.modality = "completed"
    candidate = FrameCandidates.model_validate(
        {
            "frames": [
                {
                    "clause": ref,
                    "action": "unlocked the gate",
                    "actor": "Ron",
                    "modality": "completed",
                    "negated": False,
                    "function": "turning_point",
                }
            ]
        }
    )
    [frame] = bind_frames(candidate, plan, development.id, {ref: []}, facts)
    decision = FrameDecision(
        supported=True,
        observed_modality="reported",
        observed_negated=False,
        observed_roles={"actor": str(frame.roles["actor"].identity_id)},
    )
    scene = SceneState(id=development.id, title=development.title)
    apply_frame_decision(frame, decision, scene)
    assert not scene.frames
    assert "did not confirm roles/modality" in scene.gaps[0]


def test_malformed_review_row_preserves_siblings_and_numeric_roster_ids():
    batch = FrameDecisions.model_validate(
        {
            "decisions": {
                "1": {"supported": True, "observed_modality": "told"},
                "2": {
                    "supported": True,
                    "observed_modality": "reported",
                    "observed_negated": False,
                    "observed_roles": {"speaker": 3},
                },
            }
        }
    )
    assert valid_decision(batch.decisions["1"]) is None
    witness = valid_decision(batch.decisions["2"])
    assert witness is not None and witness.observed_roles == {"speaker": "3"}


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
    authored = PlainScene(paragraphs=["Mira reached the gate. Ron D. Vale was inside."])
    alignment = SceneAlignment.model_validate(
        {
            "spans": [
                {"span": 1, "frames": ["1"]},
                {"span": 2, "frames": ["/2"]},
            ]
        }
    )
    paragraphs = aligned_scene(authored, alignment, {"1", "2"})
    assert " ".join(c.text for c in paragraphs[0].claims) == authored.paragraphs[0]
    assert paragraphs[0].claims[1].clauses == ["2"]
    with pytest.raises(ValueError, match="foreign frame"):
        aligned_scene(authored, alignment, {"1", "3"})
    alignment.spans.pop()
    with pytest.raises(ValueError, match="account for every authored span"):
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

    async def checkpoint() -> None:
        pass

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        if "s1" in packet:
            assert evidence[1].text in packet["s1"]["evidence"]
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": ref,
                        "verdict": "unsupported"
                        if ref
                        in {
                            "check-1",
                            "check-3",
                            "check-4",
                            "check-5",
                        }
                        else "supported",
                        "reason": "Evidence inspected",
                    }
                    for ref in packet
                ],
            }
        )

    result = await assess_in_batches(
        draft, plan, notes, reviewer, {}, checkpoint, review_editorial=False
    )
    assert result.claims[0].verdict == "supported"
    assert any("Unrepresented required note 2" in issue for issue in result.coverage_issues)
    assert revision_note_targets(draft, plan, notes) == {1: {"1"}}


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
        calls.extend(row["sentence"] for row in packet.values())
        decisions = [
            {
                "id": i,
                "verdict": "unsupported"
                if i in {"check-1", "check-3", "check-4", "check-5"}
                else "supported",
                "reason": "Evidence checked",
            }
            for i in packet
        ]
        if "Mira tried to open it." in calls and calls.count("Mira tried to open it.") <= 2:
            decisions = []
        return schema.model_validate({"decisions": decisions})

    partial = await assess_in_batches(draft, plan, notes, reviewer, cache, checkpoint)
    assert [c.index for c in partial.claims] == [0]
    assert partial.grounding_unavailable == [1]
    assert partial.qualification_passed is False
    assert not review_ok(partial, 2)
    assert checkpoints == [1, 2]
    result = await assess_in_batches(draft, plan, notes, reviewer, cache, checkpoint)
    assert result.qualification_passed
    assert not result.grounding_unavailable
    assert calls.count("The gate stayed closed.") == 1
    assert calls.count("Mira tried to open it.") == 3
    assert all(calls.count(str(case["text"])) == 1 for case in ROLE_CALIBRATION)
    assert checkpoints == [1, 2, 3, 4]
    unchanged = await assess_in_batches(
        draft,
        plan.model_copy(update={"revision": "new-unrelated-plan-revision"}),
        notes,
        reviewer,
        cache,
        checkpoint,
    )
    assert unchanged.claims == result.claims
    assert calls.count("The gate stayed closed.") == 1
    assert calls.count("Mira tried to open it.") == 3

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

    async def many_editorial_issues(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        assert "paragraphs" in json.loads(prompt.split("\n", 1)[1])
        return schema.model_validate(
            {
                "editorial_issues": [f"Observed editorial issue {i}." for i in range(13)],
                "originality_issues": [],
                "coverage_issues": [],
                "revise_paragraphs": [],
            }
        )

    result = await assess_in_batches(draft, plan, notes, many_editorial_issues, cache, checkpoint)
    assert result.editorial_review_available
    assert len(result.coherence_issues) == 12
    assert not result.coherent and not review_ok(result, 2)


async def test_grounding_never_uses_positive_vote_to_resolve_conflicting_decisions():
    packet = {key: {"sentence": f"Claim {key}."} for key in ("s1", "s2", "s3")}
    cache: dict[str, dict[str, object]] = {}
    calls = []

    async def checkpoint() -> None:
        pass

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        supplied = json.loads(prompt.split("\n", 1)[1])
        calls.append(list(supplied))

        def decision(key: str, verdict: str) -> dict[str, str]:
            return {"id": key, "verdict": verdict, "reason": "Evidence checked"}

        if len(calls) == 1:
            return schema.model_validate(
                {
                    "decisions": [
                        decision("s1", "supported"),
                        decision("s2", "supported"),
                        decision("s2", "unsupported"),
                        {"id": "s3", "verdict": "broken"},
                    ]
                }
            )
        return schema.model_validate(
            {
                "decisions": [
                    decision(
                        key,
                        "unsupported"
                        if key in {"check-1", "check-3", "check-4", "check-5"}
                        else "supported",
                    )
                    for key in supplied
                ]
            }
        )

    result = await grounding_rows(packet, reviewer, cache, checkpoint, tuple)
    assert set(result) == {"s1", "s3"}
    assert calls[-1] == ["s2", "s3"]
    resumed = await grounding_rows(packet, reviewer, cache, checkpoint, tuple)
    assert set(resumed) == {"s1", "s3"}
    assert calls[-2:] == [["s2"], ["s2"]]


async def test_grounding_withholds_relabelled_support_when_explanation_disagrees():
    cache: dict[str, dict[str, object]] = {}

    async def checkpoint() -> None:
        pass

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": ref,
                        "verdict": "supported",
                        "entails_all": False,
                        "reason": "The archive establishes each arrival but not travel together.",
                    }
                    for ref in packet
                ]
            }
        )

    result = await grounding_rows(
        {"s1": {"sentence": "They traveled together."}}, reviewer, cache, checkpoint, tuple
    )
    assert not result
    assert {"conflicting_verdicts": True} in cache.values()


async def test_grounding_retains_claims_and_calibration_across_provider_changes():
    packet = {f"s{i}": {"sentence": f"Claim {i}."} for i in range(1, 23)}
    cache: dict[str, dict[str, object]] = {}
    first, fallback = ("groq", "reviewer-a", None), ("ollama", "reviewer-b", "digest")
    identity = first
    calls: list[list[str]] = []

    async def checkpoint() -> None:
        pass

    async def reviewer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        nonlocal identity
        supplied = json.loads(prompt.split("\n", 1)[1])
        calls.append(list(supplied))
        keys = list(supplied)
        if len(calls) == 1:
            keys.remove("s22")
        if len(calls) == 2:
            keys.remove("check-5")
        if len(calls) == 3:
            identity = fallback
        if len(calls) == 4:
            identity = first
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": key,
                        "verdict": "unsupported"
                        if key.startswith("check-") and key != "check-2"
                        else "supported",
                        "reason": "Evidence inspected",
                        "anchors": supplied[key].get("evidence", [])[:1],
                    }
                    for key in keys
                ]
            }
        )

    result = await grounding_rows(packet, reviewer, cache, checkpoint, lambda: identity)
    assert not result
    assert calls[2] == ["check-5"]
    assert calls[3] == ["s22"]
    assert len([row for row in cache.values() if "decision" in row]) == 22
    result = await grounding_rows(packet, reviewer, cache, checkpoint, lambda: identity)
    assert len(result) == 22
    assert calls[4:] == [["check-5"]]
    observations = [row for row in cache.values() if "decision" in row]
    assert all(row["reviewer"] == list(first) and row["response_id"] for row in observations)
    partial_fallback = next(row for row in cache.values() if row.get("reviewer") == list(fallback))
    assert partial_fallback["calibration_verdicts"] == {"check-5": "unsupported"}
    assert "passed" not in partial_fallback
    identity = fallback
    result = await grounding_rows(
        {"s1": packet["s1"]},
        reviewer,
        cache,
        checkpoint,
        lambda: identity,
        dependency="changed-archive",
    )
    assert list(result) == ["s1"]
    assert calls[-2:] == [["s1"], ["check-1", "check-2", "check-3", "check-4"]]
    assert partial_fallback["passed"] is True
    assert any(
        "decision" in row and row.get("reviewer") == list(fallback) for row in cache.values()
    )


@pytest.mark.parametrize("repeats_rejection", [False, True])
async def test_section_repairs_omissions_before_edit_and_rechecks_new_facts(
    monkeypatch, repeats_rejection
):
    proposal, facts, evidence, *scope = material()
    plan = plan_from_proposal(proposal, facts, evidence, *scope)
    plan.factual.status = plan.structural.status = "passed"
    refs = sorted(clause_map(plan), key=lambda ref: clause_map(plan)[ref][1].fact_id)
    notes = FrameCitations(notes=[FrameCitation(id=ref, essential=True) for ref in refs])
    initial = "Ron opened the gate and carried Mira through it."
    repaired = ["Mira tried to open the gate.", "Ron opened the gate."]
    replacement = "Mira rode through the gate with Ron."
    order = []

    def draft(sentences, frame_ids):
        return bind_writing_notes(
            ProseDraft.model_validate(
                {
                    "paragraphs": [
                        {
                            "claims": [
                                {"text": text, "clauses": [ref]}
                                for text, ref in zip(sentences, frame_ids, strict=True)
                            ]
                        }
                    ]
                }
            ),
            plan,
            notes,
            "Gate",
        )

    async def compose(*args, repair=None, edit=None, **kwargs):
        if repair:
            order.append("repair")
            assert repair["targets"][0]["missing"] == ["1"]
            assert repair["rejected_claims"][0]["do_not_repeat"] == initial
            if repeats_rejection:
                return draft([repaired[0], initial], ["1", "2"])
            return draft(repaired, ["1", "2"])
        if edit:
            order.append("edit")
            assert edit["protected_frames"] == ["1", "2"]
            return draft([replacement], ["2"])
        order.append("initial")
        return draft([initial], ["2"])

    async def reviewer(prompt, schema, task):
        packet = json.loads(prompt.split("\n", 1)[1])
        if "paragraphs" in packet:
            order.append("editorial")
            return schema.model_validate(
                {
                    "editorial_issues": ["The sentences need a smoother transition."],
                    "originality_issues": [],
                    "coverage_issues": [],
                    "revise_paragraphs": [1],
                }
            )
        rejected = {"check-1", "check-3", "check-4", "check-5"}
        if "s1" in packet:
            order.append("ground")
            if packet["s1"]["sentence"] in {initial, replacement}:
                rejected.add("s1")
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": ref,
                        "verdict": "unsupported" if ref in rejected else "supported",
                        "reason": "Evidence checked",
                    }
                    for ref in packet
                ],
            }
        )

    async def checkpoint():
        pass

    monkeypatch.setattr(arc_prose, "compose_reconstruction", compose)
    diagnostics = {}
    result, assessment = await arc_prose.compose_grounded_section(
        Reconstruction(),
        plan,
        notes,
        "Gate",
        reviewer,
        {},
        checkpoint,
        tuple,
        diagnostics=diagnostics,
    )
    if repeats_rejection:
        assert order == ["initial", "ground", "repair"]
        assert diagnostics["repair_unavailable"] == "Repair repeated a rejected sentence"
        assert result.paragraphs[0].text == initial
        assert not review_ok(assessment, 1)
        return
    assert order[:6] == ["initial", "ground", "repair", "ground", "editorial", "edit"]
    assert order[6] == "ground"
    assert diagnostics["edit_withheld"] is True
    assert diagnostics["edited_review"]["claims"][0]["verdict"] == "unsupported"
    assert result.paragraphs[0].text == " ".join(repaired)
    assert not review_ok(assessment, 2)


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

    checkpoints = []

    async def checkpoint() -> None:
        checkpoints.append(True)

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        packet = json.loads(prompt.split("\n", 1)[1])
        if "s2" in packet:
            assert packet["s2"]["nearby_prose"] == "Ada was at the bridge."
            assert packet["s2"]["archive_alternatives"] == {
                "a1": "At the bridge Ada raised the lantern."
            }
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "id": key,
                        "verdict": "unsupported"
                        if key in {"check-1", "check-3", "check-4", "check-5"}
                        else "supported",
                        "reason": "Evidence checked",
                        "anchors": ["made-up-id"] if key == "s2" else [],
                    }
                    for key in packet
                ]
            }
        )

    review = await assess_in_batches(draft, plan, notes, infer, {}, checkpoint)
    assert [c.index for c in review.claims] == [0]
    assert review.grounding_unavailable == [1]
    assert checkpoints == [True, True]


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


def test_plan_reference_namespaces_bind_exactly_and_reject_fact_as_evidence():
    proposal, facts, evidence, *scope = material()
    baseline = plan_from_proposal(proposal, facts, evidence, *scope)
    for development in proposal.developments:
        development.anchor_ids = [f"evidence-{ref}" for ref in development.anchor_ids]
        for clause in development.clauses:
            clause.fact_id = f"fact-{int(clause.fact_id[1:]) + 1}"
            clause.evidence_ids = [f"evidence-{ref}" for ref in clause.evidence_ids]
    rebound = plan_from_proposal(proposal, facts, evidence, *scope)
    assert rebound.developments == baseline.developments
    assert rebound.ordering == baseline.ordering
    proposal.developments[0].clauses[0].evidence_ids = ["fact-1"]
    with pytest.raises(ValueError, match="Unknown development evidence"):
        plan_from_proposal(proposal, facts, evidence, *scope)


def test_plan_reconciles_exact_duplicate_but_preserves_distinct_assertion_accounting():
    proposal, facts, evidence, *scope = material()
    facts[0].update(kind="entity", target_id=str(uuid4()))
    duplicate = {**facts[0], "id": "additional-source-assertion"}
    plan = plan_from_proposal(proposal, [*facts, duplicate], evidence, *scope)
    assert plan.omissions[-1].reason == "duplicate"
    assert plan.omissions[-1].fact_ids == [duplicate["id"]]
    duplicate["target_id"] = str(uuid4())
    with pytest.raises(ValueError, match="Unaccounted references"):
        plan_from_proposal(proposal, [*facts, duplicate], evidence, *scope)


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
