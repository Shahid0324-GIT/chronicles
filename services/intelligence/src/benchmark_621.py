"""Run controlled archive reconstruction with the existing arc services."""

import argparse
import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel
from sqlalchemy import select

from src.application.arc_contracts import (
    ArcDossier,
    ArcSectionCoverage,
    ArcSectionDossier,
    ArcSectionPlan,
    DevelopmentEvidence,
    NarrativeDevelopmentPlan,
)
from src.application.arc_intelligence import ArcIntelligence, article_markdown
from src.application.arc_prose import (
    SECTION_REVISION,
    PlainScene,
    Propositions,
    SceneProse,
    compose_grounded_section,
    frame_citations,
    validate_propositions,
)
from src.application.arc_reconstruction import Reconstruction, build_discourse
from src.application.controlled_narrative import FixedDevelopmentEvidence, reference_assertions
from src.application.development_plan import clause_map
from src.application.event_extraction import evidence_units
from src.application.research_contracts import InferenceFailure, Task
from src.domain.research import SourcePassage, digest
from src.infrastructure.config.settings import Settings
from src.infrastructure.inference import create_inference
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.evidence_index import SqlEvidenceIndex
from src.infrastructure.persistence.models.research import SourceDocumentModel, SourcePassageModel
from src.infrastructure.research_runtime import build_atlas

U, C, A = map(
    UUID,
    (
        "db33dec2-5da5-53f2-9a1f-d43009d50dba",
        "9110bdd8-a094-570f-827b-ad75793989cd",
        "757483a7-667c-5caf-9e49-64f6d8772839",
    ),
)
SCOPES: dict[str, tuple[str, list[tuple[str, str | None, str | None]]]] = {
    "origin": (
        "Luffy's Origin and Devil Fruit Acquisition",
        [
            ("70ac2c1f-0e61-5643-9b4c-15d635878728", None, None),
            (
                "bcdc9aed-cff3-53d7-9895-b329a0109068",
                "Shanks decides that they have spent too much time here",
                "Timeskip forward",
            ),
        ],
    ),
    "voyage": (
        "Luffy's First Voyage and Meeting Koby",
        [
            (
                "6bb24512-ba6b-5c63-8c7c-96c70e88a689",
                "On the High Seas: Luffy's First Voyage",
                "The Oppressive Axe of the Marines",
            ),
        ],
    ),
}


class MemoryPresentation:
    def __init__(self) -> None:
        self.rows: dict[UUID, dict[str, Any]] = {}
        self.prose_checkpoint: Path | None = None

    async def get(self, identifier: UUID) -> dict[str, Any] | None:
        return self.rows.get(identifier)

    async def save(
        self,
        identifier: UUID,
        universe: UUID,
        continuity: UUID,
        resource: UUID,
        kind: str,
        boundary: str,
        revision: str,
        evidence: str,
        language: str,
        policy: str,
        payload: dict[str, Any],
        status: str,
        provider: list[dict[str, Any]],
    ) -> None:
        self.rows[identifier] = dict(
            payload=payload,
            knowledge_revision=revision,
            evidence_fingerprint=evidence,
            grounding_status=status,
        )
        if kind == "arc_prose_batches" and self.prose_checkpoint is not None:
            temporary = self.prose_checkpoint.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload), encoding="utf8")
            temporary.replace(self.prose_checkpoint)


class BenchmarkArc(ArcIntelligence):
    dossier: ArcDossier

    async def read(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"dossier": self.dossier.model_dump(mode="json")}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", choices=SCOPES)
    phase = parser.add_mutually_exclusive_group()
    phase.add_argument("--freeze", action="store_true")
    phase.add_argument("--resume-review", action="store_true")
    phase.add_argument("--compose", action="store_true")
    phase.add_argument("--stabilize", action="store_true")
    phase.add_argument("--original", action="store_true")
    parser.add_argument("--follow-up", action="store_true")
    parser.add_argument("--autonomous", action="store_true")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--scene", action="store_true")
    parser.add_argument("--relationships", action="store_true")
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--handoff", action="store_true")
    parser.add_argument("--verified-frames", action="store_true")
    parser.add_argument("--reconstruction-only", action="store_true")
    parser.add_argument("--reuse-checkpoint", type=Path)
    parser.add_argument("--writer-only", action="store_true")
    parser.add_argument("--grounded-replay", action="store_true")

    parser.add_argument("--unresolved-clause", action="append", default=[])
    parser.add_argument("--retry-relationships", action="store_true")
    parser.add_argument("--recompose", action="store_true")
    parser.add_argument("--finish-review", action="store_true")
    parser.add_argument("--refresh-notes", action="store_true")
    parser.add_argument("--resume-automatic-notes", action="store_true")
    parser.add_argument("--reviewed-notes", type=Path)
    args = parser.parse_args()
    if args.reconstruction_only and not args.verified_frames:
        parser.error("Reconstruction-only runs require --verified-frames")
    if args.reuse_checkpoint and not (args.verified_frames and args.original and args.autonomous):
        parser.error("Checkpoint reuse requires a new autonomous verified-frame benchmark")
    if args.grounded_replay and not args.writer_only:
        parser.error("Grounded replay requires the saved writer benchmark")
    if args.writer_only and not args.reuse_checkpoint:
        parser.error("A writer-only run requires a saved reconstruction checkpoint")
    if args.unresolved_clause and not args.writer_only:
        parser.error("Only the diagnostic writer can omit unresolved clauses")
    if args.autonomous and args.reviewed_notes:
        parser.error("Autonomous runs cannot load reviewed notes")
    if args.resume_automatic_notes and not (args.autonomous and args.compose):
        parser.error("Resuming automatic notes requires --autonomous --compose")
    if args.finish_review and (
        not (args.deep and args.compose) or args.refresh_notes or args.reviewed_notes
    ):
        parser.error("Finishing review requires --deep --compose and a saved draft")
    section_key = args.section
    title, ranges = SCOPES[section_key]
    baseline = Path("../../.tmp/benchmark621") / section_key
    folder = Path("../../.tmp") / ("benchmark623-follow-up" if args.follow_up else "benchmark623")
    if args.autonomous:
        folder = Path("../../.tmp/benchmark623-autonomous")
    if args.deep:
        if not args.autonomous:
            parser.error("Deep runs require --autonomous")
        folder = Path("../../.tmp/benchmark623-deep")
    if args.scene:
        if not args.autonomous:
            parser.error("Scene runs require --autonomous")
        folder = Path("../../.tmp/benchmark624")
    if args.relationships:
        if not args.scene:
            parser.error("Relationship benchmarks require --scene")
        folder = Path("../../.tmp/benchmark624-relationships")
    if args.recovery:
        if not args.relationships:
            parser.error("Recovery runs require --relationships")
        folder = Path("../../.tmp/benchmark624-recovery")
    if args.handoff:
        if not args.recovery:
            parser.error("Handoff runs require --recovery")
        folder = Path("../../.tmp/benchmark624-handoff")
    if args.verified_frames:
        if not args.handoff:
            parser.error("Verified frame runs require --handoff")
        folder = Path("../../.tmp") / (
            "benchmark625-grounded"
            if args.grounded_replay
            else "benchmark625-flow"
            if args.writer_only
            else "benchmark625-recovery-check"
        )
    folder /= section_key
    if args.freeze:
        folder = baseline
    folder.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    settings = settings.model_copy(
        update={
            "ai_provider_mode": "cloud",
            "groq_structured_output_method": (
                "json_mode" if args.follow_up or args.autonomous else "json_schema"
            ),
            "groq_structured_output_strict": False,
            "ai_max_attempts": 2 if args.autonomous else 1,
            "agent_stage_model_calls": {
                **settings.agent_stage_model_calls,
                "presentation": 29 if args.recovery else 20,
                "presentation_verification": 46 if args.verified_frames else 26,
            }
            if args.relationships
            else settings.agent_stage_model_calls,
            "agent_max_model_calls": 60
            if args.verified_frames
            else 30
            if args.handoff
            else 44
            if args.recovery
            else 44
            if args.relationships
            else 30
            if args.scene
            else 32
            if args.deep
            else 12
            if args.follow_up or args.autonomous
            else 6,
            "ai_cloud_rate_limit_wait_seconds": 75 if args.autonomous else 0,
        }
    )
    engine, factory = create_database(settings.database_url)
    units = []
    urls = {}
    async with factory() as session:
        ids = [UUID(r[0]) for r in ranges]
        metadata = await SqlEvidenceIndex(session).source_metadata(U, C, ids)
        if set(ids) != set(metadata):
            raise ValueError("Archived permission or continuity mismatch")
        for source_id, begin, end in ranges:
            identifier = UUID(source_id)
            source = await session.get(SourceDocumentModel, identifier)
            if source is None:
                raise ValueError("Fixed source is missing from the archive")
            meta = metadata[identifier]
            if not (
                meta.get("import_cloud_allowed")
                or (meta.get("public_web") and meta.get("cloud_content_allowed"))
            ):
                raise ValueError(
                    "Fixed material not currently permitted for configured cloud provider"
                )
            if source.content_hash != digest(source.text):
                raise ValueError("Source content changed")
            urls[source_id] = source.url
            first = source.text.index(begin) if begin else 0
            last = source.text.index(end, first) if end else len(source.text)
            rows = await session.scalars(
                select(SourcePassageModel)
                .where(SourcePassageModel.source_id == identifier)
                .order_by(SourcePassageModel.start)
            )
            for p in rows:
                lo = max(first, p.start)
                hi = min(last, p.end)
                if hi <= lo:
                    continue
                fragment = source.text[lo:hi]
                if p.text[lo - p.start : hi - p.start] != fragment:
                    raise ValueError("Mismatched archive passage")
                passage = SourcePassage(
                    p.id, identifier, p.ordinal, lo, hi, fragment, p.content_hash
                )
                for unit in evidence_units([passage]):
                    start = lo + unit["start"]
                    value = unit["text"]
                    units.append(
                        DevelopmentEvidence(
                            id=digest(f"{identifier}:{source.content_hash}:{start}:{value}"),
                            source_id=identifier,
                            source_hash=source.content_hash,
                            passage_id=p.id,
                            passage_hash=p.content_hash,
                            passage_start=p.start,
                            start=start,
                            end=start + len(value),
                            text=value,
                            eligibility_boundary=meta["presentation_position"],
                            position_basis=meta["position_basis"],
                            authority=meta.get("authority"),
                            source_group=source.publisher,
                        )
                    )
    await engine.dispose()
    evidence = FixedDevelopmentEvidence(U, C, units)
    facts = reference_assertions(units, urls)
    manifest = {
        "section": title,
        "input_revision": evidence.revision,
        "sources": urls,
        "units": [u.model_dump(mode="json", exclude={"text"}) for u in units],
        "live_web_requests": 0,
    }
    manifest_path = folder / "evidence-mapping.json"
    if manifest_path.exists():
        frozen = json.loads(manifest_path.read_text(encoding="utf8"))
        if frozen["input_revision"] != evidence.revision:
            raise ValueError("Archived evidence differs from the frozen dossier")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf8")
    if args.freeze:
        print(section_key, len(units), evidence.revision, flush=True)
        return
    section = ArcSectionDossier(
        id=uuid5(A, section_key),
        plan=ArcSectionPlan(
            key=section_key,
            title=title,
            objective="Reconstruct the complete section covered by the frozen reference sources.",
        ),
        developments=[],
        coverage=ArcSectionCoverage(
            research="partial",
            presentation="not_ready",
            supported_facets=[],
            missing_facets=[],
            gaps=[],
        ),
        revision=evidence.revision,
    )
    dossier = ArcDossier(
        arc_id=A,
        universe_id=U,
        continuity_id=C,
        title=title,
        claims_origin="controlled_reference_dossier",
        perspective="bounded",
        spoiler_position=7,
        source_range=(1, 7),
        sections=[section],
        accepted_facts=facts,
        reconstruction={},
        revision=evidence.revision,
    )
    memory = MemoryPresentation()

    @asynccontextmanager
    async def transaction() -> AsyncIterator[MemoryPresentation]:
        yield memory

    prior = []
    writing_notes = None
    result_path = folder / "result.json"
    if result_path.exists() and not (args.resume_review or args.compose or args.writer_only):
        raise ValueError("This fixed dossier already has a saved result. Resume the saved review.")
    if args.resume_review or args.compose or args.stabilize or args.original:
        saved_path = args.reuse_checkpoint or (
            Path("../../.tmp/benchmark624-handoff") / section_key / "result.json"
            if args.verified_frames and args.original
            else Path("../../.tmp/benchmark624-recovery") / section_key / "result.json"
            if args.handoff and args.original
            else Path("../../.tmp/benchmark624-relationships") / section_key / "result.json"
            if args.recovery and args.original
            else Path("../../.tmp/benchmark624") / section_key / "result.json"
            if args.relationships and args.original
            else Path("../../.tmp/benchmark623-deep") / section_key / "result.json"
            if args.scene and args.original
            else Path("../../.tmp/benchmark622") / section_key / "result.json"
            if args.original
            else baseline / "result.json"
            if args.stabilize
            else result_path
        )
        saved = json.loads(saved_path.read_text(encoding="utf8"))
        if saved["input_revision"] != evidence.revision:
            raise ValueError("Fixed dossier fingerprint changed")
        if args.autonomous and saved.get("reviewed_notes_input"):
            raise ValueError("Autonomous runs cannot resume a human-reviewed benchmark")
        row = saved["stored_plan"]
        if not row or not row["payload"].get("plan"):
            raise ValueError("Resume requires a saved structured plan")
        memory.rows[
            ArcIntelligence.identifier(section.id, "arc_development_plan", evidence.revision)
        ] = row
        if not (args.stabilize or args.original):
            prior = saved["provider_usage"]
        reuse_draft = not (args.original or args.refresh_notes or args.reviewed_notes)
        pending = saved.get("pending_review") if reuse_draft and not args.recompose else None
        if pending:
            memory.rows[
                ArcIntelligence.identifier(section.id, "arc_pending_review", evidence.revision)
            ] = pending
        writing_notes = (
            saved.get("writing_notes")
            if reuse_draft or (args.scene and args.original and not args.verified_frames)
            else None
        )
        if writing_notes:
            memory.rows[
                ArcIntelligence.identifier(section.id, "arc_writing_notes", evidence.revision)
            ] = writing_notes
        if saved.get("review_batches") and (
            args.reuse_checkpoint or not (args.verified_frames and args.original)
        ):
            memory.rows[
                ArcIntelligence.identifier(section.id, "arc_prose_batches", evidence.revision)
            ] = saved["review_batches"]
    if args.grounded_replay and result_path.exists():
        previous = json.loads(result_path.read_text(encoding="utf8"))
        if previous["input_revision"] != evidence.revision:
            raise ValueError("Saved writer budget belongs to a different evidence revision")
        prior = previous["provider_usage"]
    router = create_inference(settings)
    router.restore_budget(prior)
    review_continuation = 0
    if args.finish_review:
        if not pending or not writing_notes or not saved.get("review_batches"):
            raise ValueError("Finishing review requires a saved draft, notes and review batches")
        if saved.get("review_continuation"):
            raise ValueError("This draft already received its bounded review continuation")
        review_continuation = 8
        router.max_calls = router.total_used + review_continuation
        router.stage_limits = {
            **router.stage_limits,
            "presentation_verification": (
                router.stage_used.get("presentation_verification", 0) + review_continuation
            ),
        }

    async def can_review(writing: int, checking: int) -> bool:
        if args.finish_review and writing:
            return False
        return (
            router.total_used + writing + checking <= router.max_calls
            and router.stage_used.get("presentation", 0) + writing
            <= router.stage_limits.get("presentation", router.max_calls)
            and router.stage_used.get("presentation_verification", 0) + checking
            <= router.stage_limits.get("presentation_verification", router.max_calls)
        )

    service = BenchmarkArc(build_atlas(factory), transaction, evidence, can_review)
    service.dossier = dossier

    def providers() -> list[dict[str, Any]]:
        return [asdict(u) for u in router.usage]

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        if (
            args.autonomous
            and args.resume_automatic_notes
            and schema is Propositions
            and prompt.startswith("Make compact writing notes")
        ):
            return Propositions.model_validate_json(
                (folder / "generated-notes.json").read_text(encoding="utf8")
            )
        result = await router.generate(
            "Use only the permitted evidence and preserve its reference scope. "
            "Output exactly the requested structure.",
            prompt,
            schema,
            task,
            public_source_content=True,
            reserve_calls=18
            if args.verified_frames and schema.__name__ in {"FrameCandidates", "FrameDecisions"}
            else 2
            if schema in (Propositions, PlainScene)
            else 0,
        )
        print(task, result.usage.provider, result.usage.status, flush=True)
        if args.writer_only and schema is PlainScene:
            stage = (
                "revised"
                if prompt.startswith(SECTION_REVISION)
                else "factual-repair"
                if prompt.startswith("Repair only")
                else "first-draft"
            )
            (folder / f"{stage}.md").write_text(
                "\n\n".join(PlainScene.model_validate(result.value).paragraphs) + "\n",
                encoding="utf8",
            )
        if schema.__name__ in {"ArcSectionDraft"}:
            (folder / "generated-draft.json").write_text(
                result.value.model_dump_json(indent=2), encoding="utf8"
            )
        if schema is SceneProse:
            with (folder / "generated-scene-passages.jsonl").open("a", encoding="utf8") as log:
                log.write(result.value.model_dump_json() + "\n")
        if schema.__name__ in {"FrameCandidates", "FrameDecisions", "PlainScene", "SceneAlignment"}:
            with (folder / "verified-frames.jsonl").open("a", encoding="utf8") as log:
                log.write(
                    json.dumps(
                        {"schema": schema.__name__, "output": result.value.model_dump(mode="json")}
                    )
                    + "\n"
                )
        if schema is Propositions:
            name = "generated-notes" if prompt.startswith("Make compact") else "note-revisions"
            (folder / f"{name}.json").write_text(
                result.value.model_dump_json(indent=2), encoding="utf8"
            )
        if schema.__name__ == "PlannedProseReview":
            with (folder / "reviews.jsonl").open("a", encoding="utf8") as reviews:
                reviews.write(result.value.model_dump_json() + "\n")
        if schema.__name__ in {
            "RelationshipCandidates",
            "RelationshipVerdicts",
            "FocusDecisions",
            "RoleFixes",
        }:
            with (folder / "relationship-review.jsonl").open("a", encoding="utf8") as log:
                log.write(result.value.model_dump_json() + "\n")
        return result.value

    if args.writer_only:
        section = ArcSectionDossier.model_validate(saved["dossier"]["sections"][0])
        dossier.sections = [section]
        writer_plan = NarrativeDevelopmentPlan.model_validate(
            saved["stored_plan"]["payload"]["plan"]
        )
        state = Reconstruction.model_validate(saved["reconstruction"]["payload"])
        unresolved = set(args.unresolved_clause)
        refs = clause_map(writer_plan)
        if unresolved - refs.keys():
            raise ValueError("Unknown unresolved clause in the saved reconstruction")
        for scene in state.scenes:
            scene.frames = [frame for frame in scene.frames if frame.clause not in unresolved]
            scene.missing_essential = list(
                dict.fromkeys(
                    [
                        *scene.missing_essential,
                        *(ref for ref in unresolved if refs[ref][0].id == scene.id),
                    ]
                )
            )
            scene.gaps.extend(f"Unresolved clause {ref}" for ref in scene.missing_essential)
        state.beats.clear()
        build_discourse(state, writer_plan)
        section.development_plan = writer_plan
        memory.rows[service.identifier(section.id, "arc_reconstruction", evidence.revision)] = {
            "knowledge_revision": section.revision,
            "payload": state.model_dump(mode="json"),
        }
        cache_path = folder / "writer-checkpoint.json"
        if not cache_path.exists() and args.grounded_replay:
            cache_path = folder.parent.parent / "benchmark625-flow" / section_key / cache_path.name
        cache = json.loads(cache_path.read_text(encoding="utf8")) if cache_path.exists() else {}
        cache_id = service.identifier(section.id, "arc_prose_batches", evidence.revision)
        memory.rows[cache_id] = {"knowledge_revision": section.revision, "payload": cache}
        memory.prose_checkpoint = folder / "writer-checkpoint.json"
        diagnostic: dict[str, Any] = {}

        async def checkpoint() -> None:
            if memory.prose_checkpoint is not None:
                temporary = memory.prose_checkpoint.with_suffix(".tmp")
                temporary.write_text(json.dumps(cache), encoding="utf8")
                temporary.replace(memory.prose_checkpoint)

        def reviewer_model() -> tuple[Any, ...]:
            usage = next(
                (
                    row
                    for row in reversed(providers())
                    if row["task"] == "presentation_verification"
                    and row["status"] in {"ok", "cache_hit"}
                ),
                {},
            )
            return tuple(usage.get(key) for key in ("provider", "model", "model_digest"))

        try:
            await service.compose(
                dossier, evidence.revision, infer, providers, section_keys=[section_key]
            )
            if not state.ready:
                try:
                    await compose_grounded_section(
                        state,
                        writer_plan,
                        frame_citations(state, writer_plan),
                        title,
                        infer,
                        cache,
                        checkpoint,
                        reviewer_model,
                        diagnostics=diagnostic,
                        can_review=can_review,
                        diagnostic_partial=True,
                    )
                except (InferenceFailure, ValueError) as error:
                    diagnostic["halted"] = getattr(error, "code", str(error))
        finally:
            (folder / "writer-checkpoint.json").write_text(
                json.dumps(memory.rows[cache_id]["payload"]), encoding="utf8"
            )
            article = memory.rows.get(
                service.identifier(A, "arc_article", evidence.revision), {}
            ).get("payload")
            result = {
                "dossier": dossier.model_dump(mode="json"),
                "article": article,
                "scene_gaps": {
                    scene.title: scene.missing_essential
                    for scene in state.scenes
                    if scene.missing_essential
                },
                "provider_usage": prior + providers(),
                "input_revision": evidence.revision,
                "diagnostic_only": diagnostic,
            }
            pending = memory.rows.get(
                service.identifier(section.id, "arc_pending_review", evidence.revision), {}
            ).get("payload")
            if pending:
                result["selected_draft"] = pending["draft"]
                (folder / "selected-draft.md").write_text(
                    "# Controlled draft\n\n"
                    + "\n\n".join(paragraph["text"] for paragraph in pending["draft"]["paragraphs"])
                    + "\n",
                    encoding="utf8",
                )
            elif prose := diagnostic.get("selected") or diagnostic.get("initial"):
                (folder / "selected-draft.md").write_text(
                    "# Withheld diagnostic draft\n\n" + "\n\n".join(prose) + "\n",
                    encoding="utf8",
                )
            result_path.write_text(json.dumps(result, indent=2), encoding="utf8")
            (folder / "article.md").write_text(article_markdown(result), encoding="utf8")
        return

    try:
        await service.prepare_developments(
            dossier,
            evidence.revision,
            infer,
            providers,
            [section_key],
            retry_withheld=args.resume_review or args.stabilize or args.retry_relationships,
            refresh_relationships=args.retry_relationships
            or (args.recovery and args.original and not args.handoff),
        )
        plan = dossier.sections[0].development_plan
        if args.relationships and plan and writing_notes:
            old_plan = NarrativeDevelopmentPlan.model_validate(
                saved["dossier"]["sections"][0]["development_plan"]
            )
            if clause_map(old_plan) == clause_map(plan):
                memory.rows[
                    ArcIntelligence.identifier(section.id, "arc_writing_notes", evidence.revision)
                ] = {**writing_notes, "knowledge_revision": section.revision}
        print(
            "plan",
            plan and (plan.factual.status, plan.structural.status),
            plan
            and (
                "relationships",
                plan.relationship_review.status,
                sum(o.statement is not None for o in plan.ordering),
            ),
            flush=True,
        )
        if args.reviewed_notes:
            if not plan:
                raise ValueError("Reviewed benchmark notes require a scoped development plan")
            packet = json.loads(args.reviewed_notes.read_text(encoding="utf8"))
            if packet["evidence_revision"] != evidence.revision or (
                packet["plan_revision"] != plan.revision
            ):
                raise ValueError("Reviewed benchmark notes do not match the frozen plan")
            reviewed = Propositions.model_validate(packet["propositions"])
            validate_propositions(plan, reviewed)
            await service.save(
                U,
                C,
                section.id,
                "arc_writing_notes",
                evidence.revision,
                section.revision,
                reviewed.model_dump(mode="json"),
                "withheld",
                [],
            )
        if (
            (args.compose or args.original or (args.verified_frames and args.resume_review))
            and plan
            and plan.factual.status == plan.structural.status == "passed"
            and (not args.relationships or plan.relationship_review.status == "passed")
        ):
            await service.compose(
                dossier,
                evidence.revision,
                infer,
                providers,
                section_keys=[section_key],
                retry_withheld=args.resume_review,
                reconstruction_only=args.reconstruction_only,
            )
    finally:
        article = memory.rows.get(service.identifier(A, "arc_article", evidence.revision), {}).get(
            "payload"
        )
        stored = memory.rows.get(
            service.identifier(section.id, "arc_development_plan", evidence.revision)
        )
        result = {
            "dossier": dossier.model_dump(mode="json"),
            "article": article,
            "stored_plan": stored,
            "provider_usage": prior + providers(),
            "input_revision": evidence.revision,
            "reviewed_notes_input": bool(args.reviewed_notes),
            "reconstruction": memory.rows.get(
                service.identifier(section.id, "arc_reconstruction", evidence.revision)
            ),
            "review_continuation": review_continuation,
            "review_batches": memory.rows.get(
                service.identifier(section.id, "arc_prose_batches", evidence.revision)
            ),
            "pending_review": memory.rows.get(
                service.identifier(section.id, "arc_pending_review", evidence.revision)
            ),
            "writing_notes": memory.rows.get(
                service.identifier(section.id, "arc_writing_notes", evidence.revision)
            ),
        }
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf8")
        markdown = (
            article_markdown(result)
            if article
            else "# Withheld\n\nDevelopment validation did not release a reader article. "
            "See result.json for the recorded decisions.\n"
        )
        (folder / "article.md").write_text(markdown, encoding="utf8")


if __name__ == "__main__":
    asyncio.run(main())
