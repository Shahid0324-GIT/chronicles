"""Verified event frames and reader order over an existing development plan."""

import json
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID, uuid5

from pydantic import Field, ValidationError

from src.application.arc_contracts import (
    ActionModality,
    DevelopmentEvidence,
    NarrativeDevelopmentPlan,
)
from src.application.arc_grounding import word_spans
from src.application.development_plan import clause_map
from src.application.knowledge_presentation import Infer, fingerprint
from src.application.research_contracts import InferenceFailure, StructuredModel

Checkpoint = Callable[[], Awaitable[None]]
Cache = dict[str, dict[str, object]]


class FrameCandidate(StructuredModel):
    clause: str
    excerpt: str = Field(default="", max_length=230)
    kind: Literal[
        "event", "state", "speech", "belief", "emotion", "decision", "promise", "revelation"
    ] = "event"
    # Historical field name retained for stored plans and benchmark consumers.
    action: str = Field(min_length=3, max_length=180, description="Atomic proposition meaning")
    actor: str = Field(default="", max_length=100)
    patient: str = Field(default="", max_length=110)
    experiencer: str = Field(default="", max_length=100)
    speaker: str = Field(default="", max_length=100)
    subject: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=120)
    purpose: str = Field(default="", max_length=140)
    outcome: str = Field(default="", max_length=110)
    modality: ActionModality
    negated: bool
    context: list[str] = Field(default_factory=list, max_length=2)
    function: Literal["setup", "conflict", "action", "turning_point", "resolution", "aftermath"]


class FrameCandidates(StructuredModel):
    frames: list[FrameCandidate] = Field(max_length=30)


class FrameDecision(StructuredModel):
    supported: bool
    reason: str = Field(default="", max_length=180)
    observed_modality: ActionModality | None = None
    modality_confirmed: bool | None = None
    evidence_id: str = ""
    contradiction: bool = False
    observed_negated: bool | None = None
    observed_roles: dict[str, str] = Field(default_factory=dict)
    witness: str = Field(default="", max_length=3000)


class FrameDecisions(StructuredModel):
    # Expose the decision schema to providers without sacrificing valid sibling rows.
    decisions: dict[str, FrameDecision | dict[str, Any]]


class Participant(StructuredModel):
    name: str
    identity_id: UUID | None = None
    identity: Literal["canonical", "source_named", "unresolved"]


class EventFrame(FrameCandidate):
    id: UUID
    development_id: UUID
    fact_id: str
    evidence_ids: list[str]
    roles: dict[str, Participant]
    verified_witness: str = ""
    revises_clause: bool = False


class ReviewOutcome(StructuredModel):
    clause: str
    status: Literal[
        "qualified",
        "provider_unavailable",
        "incomplete_response",
        "missing_witness",
        "invalid_witness",
        "missing_modality",
        "unsupported",
        "contradiction",
        "unresolved_identity",
    ]
    detail: str = ""


class SceneState(StructuredModel):
    id: UUID
    title: str
    frames: list[EventFrame] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    review_unavailable: list[str] = Field(default_factory=list)
    review_outcomes: dict[UUID, ReviewOutcome] = Field(default_factory=dict)
    pending_essential: list[str] = Field(default_factory=list)
    presentation_layers: list[list[UUID]] = Field(default_factory=list)
    unordered_frame_ids: list[UUID] = Field(default_factory=list)
    relationship_ids: list[str] = Field(default_factory=list)
    qualification: Literal["blocked", "sufficient", "sufficient_partial"] = "blocked"
    missing_essential: list[str] = Field(default_factory=list)
    essential_clauses: list[str] = Field(default_factory=list)


class DiscourseBeat(StructuredModel):
    scene_id: UUID
    frame_ids: list[UUID]
    introductions: list[str]
    known_participants: list[str]
    prior_outcomes: list[str]
    connections: list[str]
    open_questions: list[str]


class Reconstruction(StructuredModel):
    scenes: list[SceneState] = Field(default_factory=list)
    beats: list[DiscourseBeat] = Field(default_factory=list)
    frame_issues: list[str] = Field(default_factory=list)
    scene_issues: list[str] = Field(default_factory=list)

    @property
    def ready(self) -> bool:
        return bool(self.beats) and not self.frame_issues and not self.scene_issues


def archive_context(plan: NarrativeDevelopmentPlan) -> dict[str, list[str]]:
    """Rank parallel passages by shared terms without establishing identity or order."""
    terms = {u.id: word_spans(u.text, 1) for u in plan.evidence}
    freq = Counter(w for values in terms.values() for w in values)
    by_id = {u.id: u for u in plan.evidence}
    context = {}
    for ref, (_, clause) in clause_map(plan).items():
        sources = {by_id[i].source_id for i in clause.evidence_ids}
        words = {w for w in word_spans(clause.clause, 1) if len(w[0]) > 3 and freq[w]}
        candidates = [
            u for u in plan.evidence if u.source_id not in sources and len(words & terms[u.id]) >= 2
        ]
        ranked = sorted(
            candidates,
            key=lambda u: (-sum(1 / freq[w] for w in words & terms[u.id]), u.start, u.id),
        )
        context[ref] = [u.id for u in ranked[:3]]
    return context


def archive_packet(unit: DevelopmentEvidence) -> dict[str, Any]:
    return {"source": str(unit.source_id), "start": unit.start, "end": unit.end, "text": unit.text}


def neighboring_archive(plan: NarrativeDevelopmentPlan) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for source in {u.source_id for u in plan.evidence}:
        ordered = sorted((u for u in plan.evidence if u.source_id == source), key=lambda u: u.start)
        for i, unit in enumerate(ordered):
            result[unit.id] = [
                u.id
                for u in ordered[max(0, i - 1) : i + 2]
                if u.id != unit.id and min(abs(u.start - unit.end), abs(unit.start - u.end)) <= 160
            ]
    return result


def participant(name: str, facts: list[dict[str, Any]], scope: UUID) -> Participant:
    matches = {
        f["target_id"]
        for f in facts
        if f["payload"].get("type") == "CHARACTER"
        and name.strip().casefold()
        in {
            label.strip().casefold()
            for label in [f["payload"].get("name", ""), *(f["payload"].get("aliases") or [])]
            if isinstance(label, str)
        }
    }
    if len(matches) == 1:
        return Participant(name=name, identity="canonical", identity_id=UUID(next(iter(matches))))
    if matches:
        return Participant(name=name, identity="unresolved")
    return Participant(
        name=name, identity="source_named", identity_id=uuid5(scope, name.strip().casefold())
    )


def bind_frames(
    candidates: FrameCandidates,
    plan: NarrativeDevelopmentPlan,
    scene: UUID,
    allowed_context: dict[str, list[str]],
    facts: list[dict[str, Any]],
    *,
    allow_correction: bool = False,
) -> list[EventFrame]:
    refs = clause_map(plan)
    frames = {}
    for f in candidates.frames:
        if f.clause not in refs or refs[f.clause][0].id != scene:
            raise ValueError("Frame references an action outside its development")
        clause = refs[f.clause][1]
        if not set(f.context) <= set(allowed_context[f.clause]):
            raise ValueError("Frame references unavailable context")
        if f.excerpt and not any(
            f.excerpt in u.text for u in plan.evidence if u.id in clause.evidence_ids
        ):
            raise ValueError("Frame excerpt is outside the exact accepted evidence")
        revises_clause = (clause.negated and not f.negated) or (
            clause.modality not in {"completed", "unknown"} and f.modality == "completed"
        )
        if revises_clause and (not allow_correction or not f.excerpt):
            if clause.negated and not f.negated:
                raise ValueError("Frame removed accepted negation without an archive correction")
            # A separate completed action inside a compound source clause remains eligible.
            if not f.excerpt or any(
                f.excerpt == u.text for u in plan.evidence if u.id in clause.evidence_ids
            ):
                raise ValueError("Frame converted a non-completed action to a completed event")
        fields = f.model_dump(mode="json")
        identifier = uuid5(scene, fingerprint([clause.fact_id, fields]))
        frames[identifier] = EventFrame(
            **fields,
            id=identifier,
            development_id=scene,
            fact_id=clause.fact_id,
            revises_clause=revises_clause,
            evidence_ids=list(dict.fromkeys([*clause.evidence_ids, *f.context])),
            roles={
                role: participant(name, facts, plan.section_id)
                for role in ("actor", "patient", "experiencer", "speaker", "subject")
                if (name := str(fields[role]))
            },
        )
    return list(frames.values())


def valid_decision(value: Any) -> FrameDecision | None:
    if isinstance(value, dict):
        value = dict(value)
        if isinstance(value.get("reason"), str):
            value["reason"] = value["reason"][:180]
        if isinstance(value.get("observed_roles"), dict):
            value["observed_roles"] = {
                k: str(v) if type(v) is int else v for k, v in value["observed_roles"].items()
            }
    try:
        return FrameDecision.model_validate(value)
    except ValidationError:
        return None


async def qualify_frames(
    frames: list[EventFrame],
    by_id: dict[str, DevelopmentEvidence],
    neighboring: dict[str, list[str]],
    infer: Infer,
    cache: Cache,
    checkpoint: Checkpoint,
    scene: SceneState,
) -> list[EventFrame]:
    packet: dict[str, Any] = {}
    remaining: list[tuple[EventFrame, str, list[str]]] = []
    for frame in frames:
        exact_correction = bool(frame.excerpt and frame.excerpt == frame.action)
        units = (
            [u for u in frame.evidence_ids if frame.excerpt in by_id[u].text]
            if exact_correction
            else frame.evidence_ids
        )
        evidence_ids = {f"e{i}": by_id[u].text for i, u in enumerate(units, 1)}
        item = {
            "proposition": {
                "kind": frame.kind,
                "meaning": frame.action,
                "modality": frame.modality,
                "negated": frame.negated,
                "participants": {role: p.name for role, p in frame.roles.items()},
                "place": frame.location,
                "purpose": frame.purpose,
                "outcome": frame.outcome,
                "anchor": frame.excerpt,
            },
            "evidence_id": evidence_ids,
            "nearby_context": []
            if exact_correction
            else [
                by_id[v].text
                for v in dict.fromkeys(
                    v
                    for u in frame.evidence_ids
                    for v in neighboring[u]
                    if v not in frame.evidence_ids
                )
            ],
        }
        key = fingerprint(["semantic-proposition-entailment-v4", item, frame.evidence_ids])
        previous_item = {k: v for k, v in item.items() if k != "evidence_id"} | {
            "evidence": list(evidence_ids.values())
        }
        previous_key = fingerprint(
            ["semantic-proposition-entailment-v2", previous_item, frame.evidence_ids]
        )
        saved = cache.get(key)
        if saved is None:
            previous = cache.get(
                fingerprint(["semantic-proposition-entailment-v3", item, frame.evidence_ids])
            )
            if previous and previous.get("supported") is True:
                saved = previous
        if saved is None and not frame.revises_clause:
            prior = cache.get(previous_key)
            if prior and prior.get("supported") is True:
                saved = prior
        if saved is not None:
            apply_frame_decision(frame, FrameDecision.model_validate(saved), scene)
        else:
            packet[str(len(packet) + 1)] = item
            remaining.append((frame, key, units))
    if not remaining:
        return []
    try:
        result = FrameDecisions.model_validate(
            await infer(
                "For every numbered proposition, check its meaning against the archive. "
                "Use nearby text only to resolve referents. A report or promise does not prove "
                "its content happened. Attempts, beliefs, and negation must stay intact. "
                "Judge modality for the proposition's main action or state. Evidence that "
                "someone was preparing establishes the preparation occurred. It does not "
                "establish completion of the action they were preparing to perform. "
                "A wound below a wrist is not a wound to the wrist. Check precise identities, "
                "location, and outcome. Ignore equivalent phrasing and role labels. Return "
                "decisions keyed by record ID. For support, return supported=true, the ID of "
                "one supporting evidence unit from evidence_id, and modality_confirmed=true "
                "only if the archive establishes the proposition's stated modality. If a "
                "claim is unsupported, give supported=false and a brief reason. Use "
                "contradiction=true only when the archive says something incompatible.\n"
                + json.dumps(packet, ensure_ascii=False, separators=(",", ":")),
                FrameDecisions,
                "presentation_verification",
            )
        )
    except InferenceFailure as error:
        for frame, _, _ in remaining:
            scene.review_outcomes[frame.id] = ReviewOutcome(
                clause=frame.clause, status="provider_unavailable", detail=error.code
            )
        return [frame for frame, _, _ in remaining]
    missing = []
    for i, (frame, key, units) in enumerate(remaining, 1):
        decision = valid_decision(result.decisions.get(str(i)))
        status = incomplete_review(frame, decision, by_id, units=units)
        if status is not None or decision is None:
            scene.review_outcomes[frame.id] = ReviewOutcome(
                clause=frame.clause, status=status or "incomplete_response"
            )
            missing.append(frame)
            continue
        apply_frame_decision(frame, decision, scene)
        cache[key] = decision.model_dump(mode="json")
    if len(missing) < len(remaining):
        await checkpoint()
    return missing


def incomplete_review(
    frame: EventFrame,
    decision: FrameDecision | None,
    by_id: dict[str, DevelopmentEvidence],
    *,
    units: list[str] | None = None,
) -> (
    Literal["incomplete_response", "missing_witness", "invalid_witness", "missing_modality"] | None
):
    if decision is None or (not decision.supported and not decision.reason.strip()):
        return "incomplete_response"
    if not decision.supported or decision.contradiction:
        return None
    offered = frame.evidence_ids if units is None else units
    if decision.evidence_id:
        permitted = {f"e{i}": u for i, u in enumerate(offered, 1)}
        unit = permitted.get(decision.evidence_id.strip().lower())
        if unit is None:
            return "invalid_witness"
        decision.witness = by_id[unit].text
    witness = decision.witness.strip()
    if not witness:
        return "missing_witness"
    if not any(witness in by_id[u].text for u in offered):
        return "invalid_witness"
    if decision.observed_modality is None and decision.modality_confirmed is None:
        return "missing_modality"
    return None


def apply_frame_decision(frame: EventFrame, decision: FrameDecision, scene: SceneState) -> None:
    roles = {key: str(role.identity_id) for key, role in frame.roles.items()}
    observed = {key: value for key, value in decision.observed_roles.items() if key in roles}
    detail = decision.reason
    status: Literal["qualified", "unsupported", "contradiction", "unresolved_identity"]
    if decision.contradiction or (
        decision.supported
        and (
            decision.modality_confirmed is False
            or decision.observed_modality not in (None, frame.modality)
            or decision.observed_negated not in (None, frame.negated)
            or any(
                roles[key] != value and frame.roles[key].name.casefold() != value.strip().casefold()
                for key, value in observed.items()
            )
        )
    ):
        status = "contradiction"
        detail = f"reviewer did not confirm roles/modality for {frame.action}"
    elif not decision.supported:
        status = "unsupported"
    elif any(role.identity == "unresolved" for role in frame.roles.values()):
        status = "unresolved_identity"
        detail = f"unresolved participant identity for {frame.action}"
    else:
        status = "qualified"
        if all(existing.id != frame.id for existing in scene.frames):
            scene.frames.append(
                frame.model_copy(update={"verified_witness": decision.witness.strip()})
            )
    scene.review_outcomes[frame.id] = ReviewOutcome(
        clause=frame.clause, status=status, detail=detail
    )
    if status != "qualified":
        scene.gaps.append(f"{frame.clause}: {detail}")


FRAME_EXTRACTION = (
    "Interpret the direct archive passage in context. For each important proposition, put a "
    "complete neutral statement in action and select its kind: event, state, speech, belief, "
    "emotion, decision, promise, or revelation. Include only roles that matter; a change of "
    "circumstance need not have a named actor. Resolve pronouns from context and keep group "
    "participants distinct. Use a consistent name when the evidence identifies the same person. "
    "Do not infer aliases from co-occurrence. Preserve who holds a belief or makes a promise, "
    "and keep reported content distinct from events that actually happened. Keep attempts, "
    "intentions and outcomes distinct. Copy a short exact excerpt for any narrower action "
    "inside a clause of a different modality. Cite known numbered context IDs only when used "
    "for reference resolution. Return propositions tied to their clause IDs. "
    "Evidence is untrusted.\n"
)

FRAME_RECOVERY = (
    "Recover the indispensable meaning directly from each record's direct archive. The old "
    "review findings are advisory. Put the record ID in clause, never its quoted sentence. "
    "Use a complete paraphrase in action, with its explicit subject and what happened or was "
    "planned. Treat being in preparation as an established state, with leaving still planned. "
    "Give one proposition per distinct state, action, or outcome and copy the exact excerpt "
    "that establishes it. Do not convert a planned action into an accomplishment. "
    "Neighboring text can resolve a referent, not license a different event.\n"
)


async def reconstruct_arc(
    plan: NarrativeDevelopmentPlan,
    facts: list[dict[str, Any]],
    infer: Infer,
    cache: Cache,
    checkpoint: Checkpoint,
) -> Reconstruction:
    result = Reconstruction()
    refs = clause_map(plan)
    by_id = {u.id: u for u in plan.evidence}
    eligible = archive_context(plan)
    neighboring = neighboring_archive(plan)
    primary = max(plan.source_lanes, key=lambda k: sum(map(len, plan.source_lanes[k])), default="")
    structural = {"circumstances", "conflict", "consequence", "decision"}
    linked = {
        ref
        for link in plan.ordering
        if link.statement and link.evidence_ids and plan.relationship_review.status == "passed"
        for ref in (link.before_clause, link.after_clause)
    }
    eligible = {
        ref: list(
            dict.fromkeys(
                [
                    *(v for u in c.evidence_ids for v in neighboring[u] if v not in c.evidence_ids),
                    *eligible[ref],
                ]
            )
        )
        for ref, (_, c) in refs.items()
    }
    labels = {f"e{i}": u.id for i, u in enumerate(plan.evidence, 1)}
    label_for = {unit: label for label, unit in labels.items()}
    for d in plan.developments:
        scene = SceneState(id=d.id, title=d.title, gaps=list(d.unresolved))
        result.scenes.append(scene)
        scoped = {k: c for k, (owner, c) in refs.items() if owner.id == d.id}
        essential = {k for k, c in scoped.items() if c.facet in structural or k in linked}
        if not essential and scoped:
            essential = {next(iter(scoped))}
        packet = {
            k: {
                "statement": c.clause,
                "modality": c.modality,
                "negated": c.negated,
                "direct": {label_for[i]: archive_packet(by_id[i]) for i in c.evidence_ids},
                "context": {label_for[i]: archive_packet(by_id[i]) for i in eligible[k]},
            }
            for k, c in scoped.items()
        }
        index_key = fingerprint(["scene-propositions-v1", plan.revision, str(d.id), packet])
        retained = {
            frame.id: frame
            for frame in (
                EventFrame.model_validate(raw) for raw in cache.get(index_key, {}).values()
            )
        }
        attempted: set[UUID] = set()

        async def review_window(
            frames: list[EventFrame],
            scene: SceneState = scene,
            attempted: set[UUID] = attempted,
            essential: set[str] = essential,
        ) -> None:
            unseen = [frame for frame in frames if frame.id not in attempted]
            attempted.update(frame.id for frame in unseen)
            essential.update(
                frame.clause
                for frame in unseen
                if (
                    frame.function in {"turning_point", "resolution"}
                    or frame.kind in {"promise", "revelation"}
                )
                and (
                    not primary
                    or any(
                        str(by_id[u].source_id) == primary
                        for u in refs[frame.clause][1].evidence_ids
                    )
                )
            )
            for start in range(0, len(unseen), 8):
                missing = await qualify_frames(
                    unseen[start : start + 8], by_id, neighboring, infer, cache, checkpoint, scene
                )
                for frame in missing:
                    if frame.clause not in scene.review_unavailable:
                        scene.review_unavailable.append(frame.clause)
                    status = scene.review_outcomes[frame.id].status
                    scene.gaps.append(f"{frame.clause}: {status} for {frame.action}")

        await review_window(list(retained.values()))
        for recovery in (False, True):
            pending_clauses = set(scene.review_unavailable)
            rejected_clauses = {
                outcome.clause
                for outcome in scene.review_outcomes.values()
                if outcome.status in {"unsupported", "contradiction", "unresolved_identity"}
            }
            remaining_clauses = essential - {f.clause for f in scene.frames}
            remaining_clauses -= pending_clauses - rejected_clauses
            if recovery and not remaining_clauses:
                break
            requested = [k for k in packet if not recovery or k in remaining_clauses]
            # Keep the original scene and archive neighbors while bounding the extractor input.
            window_size = 6 if len(requested) > 8 else 8
            for start_of_window in range(0, len(requested), window_size):
                window = requested[start_of_window : start_of_window + window_size]
                request = {k: packet[k] for k in window}
                if recovery:
                    request = {
                        k: {
                            "direct": row["direct"],
                            "context": row["context"],
                            "revision_findings": [
                                outcome.detail
                                for outcome in scene.review_outcomes.values()
                                if outcome.clause == k
                                and outcome.status
                                in {"unsupported", "contradiction", "unresolved_identity"}
                            ],
                        }
                        for k, row in request.items()
                    }
                key = fingerprint(
                    [
                        "semantic-proposition-recovery-v3"
                        if recovery
                        else "semantic-proposition-extraction-v1",
                        request,
                    ]
                )
                try:
                    extracted = FrameCandidates.model_validate(
                        cache[key]
                        if key in cache
                        else await infer(
                            FRAME_EXTRACTION
                            + (FRAME_RECOVERY if recovery else "")
                            + json.dumps(request, ensure_ascii=False),
                            FrameCandidates,
                            "presentation",
                        )
                    )
                    proposed = []
                    for candidate in extracted.frames:
                        try:
                            if candidate.clause not in request:
                                # Recover a direct label or quote in the clause slot.
                                anchor = candidate.clause.strip().lower()
                                unit_id = labels.get(anchor, anchor)
                                owners = [
                                    ref
                                    for ref in request
                                    if unit_id in scoped[ref].evidence_ids
                                    or any(
                                        candidate.clause.strip() == by_id[u].text.strip()
                                        for u in scoped[ref].evidence_ids
                                    )
                                ]
                                if len(owners) == 1:
                                    updates = {"clause": owners[0]}
                                    # Require an exact direct unit for quote reuse.
                                    if (
                                        recovery
                                        and candidate.clause == candidate.excerpt
                                        and len(candidate.action.split()) == 1
                                        and len(candidate.excerpt) <= 180
                                        and any(
                                            candidate.excerpt == by_id[u].text
                                            for u in scoped[owners[0]].evidence_ids
                                        )
                                    ):
                                        updates["action"] = candidate.excerpt
                                    candidate = candidate.model_copy(update=updates)
                            if candidate.clause not in request:
                                raise ValueError(
                                    "Frame references a clause outside the current request"
                                )
                            allowed = set(eligible[candidate.clause])
                            context = [
                                labels.get(ref.strip().lower(), ref.strip())
                                for ref in candidate.context
                            ]
                            licensed = list(dict.fromkeys(ref for ref in context if ref in allowed))
                            if len(licensed) < len(set(context)):
                                scene.gaps.append(
                                    f"{candidate.clause}: unresolved context reference omitted"
                                )
                            candidate = candidate.model_copy(update={"context": licensed})
                            proposed.extend(
                                bind_frames(
                                    FrameCandidates(frames=[candidate]),
                                    plan,
                                    d.id,
                                    eligible,
                                    facts,
                                    allow_correction=recovery,
                                )
                            )
                        except ValueError as error:
                            scene.gaps.append(f"{candidate.clause}: {error}")
                    proposed = list({f.id: f for f in proposed}.values())
                    new_frames = [f for f in proposed if f.id not in retained]
                    if key not in cache or new_frames:
                        cache[key] = extracted.model_dump(mode="json")
                        retained.update((f.id, f) for f in new_frames)
                        cache[index_key] = {
                            str(f.id): f.model_dump(mode="json") for f in retained.values()
                        }
                        await checkpoint()
                    await review_window(proposed)
                except (InferenceFailure, ValueError) as error:
                    code = error.code if isinstance(error, InferenceFailure) else str(error)[:160]
                    scene.gaps.append(f"Frame validation unavailable ({code})")
        scene.essential_clauses = [ref for ref in scoped if ref in essential]
        covered = {f.clause for f in scene.frames}
        missing_clauses = scoped.keys() - covered - set(scene.review_unavailable)
        if missing_clauses:
            scene.gaps.append("Unverified accepted clauses: " + ", ".join(sorted(missing_clauses)))
        scene.pending_essential = sorted((essential - covered) & set(scene.review_unavailable))
        scene.missing_essential = sorted(essential - covered - set(scene.pending_essential))
        if scene.pending_essential:
            result.frame_issues.append(
                f"{d.title}: essential review pending " + ", ".join(scene.pending_essential)
            )
        if scene.missing_essential:
            result.frame_issues.append(
                f"{d.title}: missing essential clauses " + ", ".join(scene.missing_essential)
            )
        elif scene.frames and not scene.pending_essential:
            scene.qualification = "sufficient_partial" if scene.gaps else "sufficient"
    build_discourse(result, plan)
    return result


def build_discourse(state: Reconstruction, plan: NarrativeDevelopmentPlan) -> None:
    """Preserve archive presentation instead of inventing story-world chronology."""
    by_id = {s.id: s for s in state.scenes}
    primary = max(plan.source_lanes, key=lambda k: sum(map(len, plan.source_lanes[k])), default="")
    lane = plan.source_lanes.get(primary, [])
    units = {u.id: u for u in plan.evidence}
    refs = clause_map(plan)
    covered = {frame.clause for scene in state.scenes for frame in scene.frames}
    order = list(dict.fromkeys([i for group in lane for i in group] + list(by_id)))
    seen: set[str] = set()
    prior_outcomes: list[str] = []
    for key in order:
        scene = by_id[key]
        positions: dict[int, list[UUID]] = {}
        unordered: list[UUID] = []
        for frame in scene.frames:
            starts = [
                units[u].start
                + (
                    units[u].text.index(frame.excerpt)
                    if frame.excerpt and frame.excerpt in units[u].text
                    else 0
                )
                for u in refs[frame.clause][1].evidence_ids
                if str(units[u].source_id) == primary
            ]
            if starts:
                positions.setdefault(min(starts), []).append(frame.id)
            else:
                unordered.append(frame.id)
        scene.presentation_layers = [positions[i] for i in sorted(positions)]
        scene.unordered_frame_ids = unordered
        names = {
            str(role.identity_id) if role.identity_id else role.name.casefold(): role.name
            for frame in scene.frames
            for role in frame.roles.values()
        }
        ordered_clauses = {f.clause for f in scene.frames}
        links = [
            link
            for link in plan.ordering
            if link.statement
            and link.evidence_ids
            and plan.relationship_review.status == "passed"
            and key in {link.before, link.after}
        ]
        scene.relationship_ids = [
            f"link-{i}" for i, link in enumerate(plan.ordering, 1) if link in links
        ]
        # Exact source positions establish presentation. Only reviewed links establish
        # a historical or explanatory connection. Unplaced core actions remain unsafe.
        unplaced = {f.clause for f in scene.frames if f.id in unordered} - {
            ref for link in links for ref in (link.before_clause, link.after_clause)
        }
        blocked_order = unplaced & set(scene.essential_clauses)
        if len(ordered_clauses) > 1 and blocked_order:
            scene.qualification = "blocked"
            state.scene_issues.append(
                f"{scene.title}: no presentation anchor or verified link for "
                + ", ".join(sorted(blocked_order))
            )
        if not scene.frames:
            state.scene_issues.append(f"{scene.title}: no qualified event frames")
        state.beats.append(
            DiscourseBeat(
                scene_id=key,
                frame_ids=[i for layer in scene.presentation_layers for i in layer] + unordered,
                introductions=sorted(names[k] for k in names.keys() - seen),
                known_participants=sorted(names[k] for k in names.keys() & seen),
                prior_outcomes=prior_outcomes[-3:],
                connections=[
                    o.statement
                    for o in links
                    if o.statement and {o.before_clause, o.after_clause} <= covered
                ],
                open_questions=scene.gaps,
            )
        )
        seen.update(names)
        prior_outcomes.extend(f.outcome for f in scene.frames if f.outcome)
