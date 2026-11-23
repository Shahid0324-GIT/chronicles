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
)
from src.application.arc_intelligence import ArcIntelligence, article_markdown
from src.application.controlled_narrative import FixedDevelopmentEvidence, reference_assertions
from src.application.event_extraction import evidence_units
from src.application.research_contracts import Task
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
    args = parser.parse_args()
    section_key = args.section
    title, ranges = SCOPES[section_key]
    folder = Path("../../.tmp/benchmark621") / section_key
    folder.mkdir(parents=True, exist_ok=True)
    settings = Settings().model_copy(
        update={
            "ai_provider_mode": "cloud",
            "groq_structured_output_method": "json_schema",
            "groq_structured_output_strict": False,
            "ai_max_attempts": 1,
            "agent_max_model_calls": 6,
            "ai_cloud_rate_limit_wait_seconds": 0,
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
    result_path = folder / "result.json"
    if result_path.exists() and not (args.resume_review or args.compose):
        raise ValueError("This fixed dossier already has a saved result. Resume the saved review.")
    if args.resume_review or args.compose:
        saved = json.loads(result_path.read_text(encoding="utf8"))
        if saved["input_revision"] != evidence.revision:
            raise ValueError("Fixed dossier fingerprint changed")
        row = saved["stored_plan"]
        if not row or not row["payload"].get("plan"):
            raise ValueError("Resume requires a saved structured plan")
        memory.rows[
            ArcIntelligence.identifier(section.id, "arc_development_plan", evidence.revision)
        ] = row
        prior = saved["provider_usage"]
    router = create_inference(settings)
    router.max_calls = max(0, router.max_calls - len(prior))
    service = BenchmarkArc(build_atlas(factory), transaction, evidence)
    service.dossier = dossier

    def providers() -> list[dict[str, Any]]:
        return [asdict(u) for u in router.usage]

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        result = await router.generate(
            "Use only the permitted evidence and preserve its reference scope. "
            "Output exactly the requested structure.",
            prompt,
            schema,
            task,
            public_source_content=True,
        )
        print(task, result.usage.provider, result.usage.status, flush=True)
        return result.value

    try:
        await service.prepare_developments(
            dossier,
            evidence.revision,
            infer,
            providers,
            [section_key],
            retry_withheld=args.resume_review,
        )
        plan = dossier.sections[0].development_plan
        print(
            "plan",
            plan and (plan.factual.status, plan.structural.status),
            dossier.sections[0].coverage.gaps,
            flush=True,
        )
        if args.compose and plan and plan.factual.status == plan.structural.status == "passed":
            await service.compose(
                dossier, evidence.revision, infer, providers, section_keys=[section_key]
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
