"""Durable arc research projections over the existing canonical evidence graph.

Model assignments are editorial organization only. They cannot add canonical
assertions. Prose has an independent artifact and grounding gate.
"""

import json
import re
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid5

from src.application.arc_contracts import (
    ArcArticle,
    ArcDossier,
    ArcPlan,
    ArcSectionCoverage,
    ArcSectionDossier,
    ArcSectionDraft,
    ArcUnderstanding,
    Facet,
)
from src.application.encyclopedia_contracts import GroundingAssessment
from src.application.knowledge_presentation import Infer, KnowledgeAtlas, fingerprint
from src.application.ports.presentation import PresentationTransaction
from src.application.research_contracts import InferenceFailure

REQUIRED: list[Facet] = [
    "circumstances",
    "development",
    "action",
    "decision",
    "conflict",
    "consequence",
]
POLICY = "arc-intelligence-v1"


def licensed_context(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """No full archive metadata or unlicensed quotation clauses in model dossiers."""
    return [
        {
            "id": str(i + 1),
            "kind": f["kind"],
            "target_id": f["target_id"],
            "type": f["payload"].get("type"),
            "statement": (f["payload"].get("atomic") or {}).get("statement")
            or f["payload"].get("description", ""),
            "positions": [
                s.get("provenance", {}).get("presentation_position") for s in f["sources"]
            ],
        }
        for i, f in enumerate(facts)
    ]


class ArcIntelligence:
    def __init__(self, atlas: KnowledgeAtlas, presentations: PresentationTransaction) -> None:
        self.atlas, self.presentations = atlas, presentations

    @staticmethod
    def identifier(arc: UUID, kind: str, boundary: str) -> UUID:
        return uuid5(arc, f"{POLICY}:{kind}:{boundary}")

    async def context(
        self,
        universe: UUID,
        continuity: UUID,
        arc: UUID,
        boundary: int | None,
        allowed_sources: list[UUID] | None = None,
    ) -> tuple[Any, Any, list[dict[str, Any]]]:
        scope = await self.atlas.scope(
            universe, continuity, allowed_sources=allowed_sources, spoiler_position=boundary
        )
        definition = next((a for a in scope.knowledge.story_scopes if a.id == str(arc)), None)
        if definition is None or definition.continuity_id != continuity:
            raise ValueError("Unknown arc in requested continuity")
        # Only accepted assertions enter the dossier. Retrospective facts require
        # an accepted graph connection to an in-range target; shared words do not suffice.
        facts = [f for values in scope.facts.values() for f in values]
        from src.application.story_position import source_position

        targets = {
            f["target_id"]
            for f in facts
            if all(
                (p := source_position(s, definition.position_basis)) is not None
                and definition.first_position <= p <= definition.last_position
                for s in f["sources"]
            )
        }
        eligible = set(targets)
        for edge in scope.edges():
            if edge.relationship_type.value == "REVEALED" and str(edge.source_node_id) in targets:
                eligible.update((str(edge.id), str(edge.target_node_id)))
        selected = [f for f in facts if f["target_id"] in eligible]
        return scope, definition, selected

    async def save(
        self,
        universe: UUID,
        continuity: UUID,
        arc: UUID,
        kind: str,
        boundary: str,
        revision: str,
        payload: dict[str, Any],
        status: str,
        providers: list[dict[str, Any]],
    ) -> None:
        async with self.presentations() as repo:
            await repo.save(
                self.identifier(arc, kind, boundary),
                universe,
                continuity,
                arc,
                kind,
                boundary,
                revision,
                revision,
                "en",
                POLICY,
                payload,
                status,
                providers,
            )

    async def read(
        self,
        universe: UUID,
        continuity: UUID,
        arc: UUID,
        boundary: int | None,
        allowed_sources: list[UUID] | None = None,
    ) -> dict[str, Any]:
        scope, definition, facts = await self.context(
            universe, continuity, arc, boundary, allowed_sources
        )
        async with self.presentations() as repo:
            stored = await repo.get(self.identifier(arc, "arc_dossier", scope.boundary))
            article = await repo.get(self.identifier(arc, "arc_article", scope.boundary))
        current = fingerprint(
            [facts, definition.model_dump(mode="json"), scope.knowledge.reference_outline]
        )
        if not stored or stored["evidence_fingerprint"] != current:
            return {
                "status": "pending",
                "reason": "Current evidence has no matching dossier",
                "dossier": None,
                "article": None,
            }
        dossier = ArcDossier.model_validate(stored["payload"])
        return {
            "status": "partial",
            "dossier": dossier.model_dump(mode="json"),
            "article": article["payload"]
            if article and article["knowledge_revision"] == dossier.revision
            else None,
        }

    async def rebuild(
        self,
        universe: UUID,
        continuity: UUID,
        arc: UUID,
        boundary: int | None,
        infer: Infer,
        providers: Callable[[], list[dict[str, Any]]],
        *,
        compose: bool = True,
    ) -> dict[str, Any]:
        scope, definition, facts = await self.context(universe, continuity, arc, boundary)
        evidence_revision = fingerprint(
            [facts, definition.model_dump(mode="json"), scope.knowledge.reference_outline]
        )
        plan_key = self.identifier(arc, "arc_plan", scope.boundary)
        async with self.presentations() as repo:
            stored_plan = await repo.get(plan_key)
        if stored_plan:
            plan = ArcPlan.model_validate(stored_plan["payload"])
        else:
            plan = ArcPlan.model_validate(
                await infer(
                    "Plan narrative sections for a whole arc. This is provisional research,"
                    " NOT canon. "
                    "Use supplied outline descriptions and scope only; never fill story "
                    "from memory. "
                    "Include missing setup, developments, conflict and resolution as QUESTIONS. "
                    "Do not equate reference citation numbers with chapter numbers. "
                    + json.dumps(
                        {
                            "arc": definition.model_dump(mode="json"),
                            "reference_outline": scope.knowledge.reference_outline,
                        }
                    ),
                    ArcPlan,
                    "planning",
                )
            )
            for section in plan.sections:
                if (
                    section.first_position and section.first_position < definition.first_position
                ) or (section.last_position and section.last_position > definition.last_position):
                    raise ValueError("Provisional section outside arc boundaries")
            await self.save(
                universe,
                continuity,
                arc,
                "arc_plan",
                scope.boundary,
                fingerprint(plan.model_dump(mode="json")),
                plan.model_dump(mode="json"),
                "provisional",
                providers(),
            )
        async with self.presentations() as repo:
            existing = await repo.get(self.identifier(arc, "arc_dossier", scope.boundary))
        if existing and existing["evidence_fingerprint"] == evidence_revision:
            dossier = ArcDossier.model_validate(existing["payload"])
        else:
            understanding = ArcUnderstanding(bindings=[])
            if facts:
                understanding = ArcUnderstanding.model_validate(
                    await infer(
                        "Organize ONLY accepted assertions into narrative section facets. "
                        "Return exact "
                        "fact_ids and section keys. Classify what the assertion actually "
                        "establishes, "
                        "not what its wider quotation implies. A lone action does not "
                        "establish initial "
                        "circumstances, decisions, conflict or consequences. Do not infer "
                        "motivation, "
                        "causality or chronology. Later REVEALED assertions belong to "
                        "retrospective "
                        "understanding. Leave unsupported facets empty. This organization "
                        "adds no canon.\n"
                        + json.dumps(
                            {
                                "plan": plan.model_dump(mode="json"),
                                "facts": licensed_context(facts),
                            },
                            ensure_ascii=False,
                        ),
                        ArcUnderstanding,
                        "relationship_analysis",
                    )
                )
            references = {str(i + 1): f["id"] for i, f in enumerate(facts)}
            for binding in understanding.bindings:
                binding.fact_ids = [references.get(i, i) for i in binding.fact_ids]
            ids = {f["id"] for f in facts}
            if any(
                b.section_key not in {s.key for s in plan.sections} or not set(b.fact_ids) <= ids
                for b in understanding.bindings
            ):
                raise ValueError("Unlicensed dossier assignment")
            sections = []
            for section in plan.sections:
                bindings = [b for b in understanding.bindings if b.section_key == section.key]
                supported = sorted({b.facet for b in bindings})
                missing = [f for f in REQUIRED if f not in supported]
                coverage = ArcSectionCoverage(
                    research="partial" if bindings else "not_researched",
                    presentation="ready" if bindings else "not_ready",
                    supported_facets=supported,
                    missing_facets=missing,
                    gaps=[f"What evidence establishes {f} in {section.title}?" for f in missing],
                )
                section_facts = [
                    f for f in facts if f["id"] in {i for b in bindings for i in b.fact_ids}
                ]
                sections.append(
                    ArcSectionDossier(
                        id=uuid5(arc, section.key),
                        plan=section,
                        developments=bindings,
                        coverage=coverage,
                        revision=fingerprint(
                            [section.model_dump(mode="json"), section_facts, bindings]
                        ),
                    )
                )
            catalog = await self.atlas.catalog(universe, continuity, spoiler_position=boundary)
            dossier = ArcDossier(
                arc_id=arc,
                universe_id=universe,
                continuity_id=continuity,
                title=definition.title,
                perspective="bounded" if boundary else "full_lore",
                spoiler_position=boundary,
                source_range=(definition.first_position, definition.last_position),
                sections=sections,
                accepted_facts=facts,
                reconstruction=next(
                    (r for r in catalog.get("reconstructions", []) if r["arcId"] == str(arc)), {}
                ),
                revision=evidence_revision,
            )
            # Recheck evidence and permission revisions after all model work.
            current_scope, current_arc, current_facts = await self.context(
                universe, continuity, arc, boundary
            )
            if (
                fingerprint(
                    [
                        current_facts,
                        current_arc.model_dump(mode="json"),
                        current_scope.knowledge.reference_outline,
                    ]
                )
                != evidence_revision
            ):
                raise ValueError("Evidence changed during dossier reconstruction")
            await self.save(
                universe,
                continuity,
                arc,
                "arc_dossier",
                scope.boundary,
                evidence_revision,
                dossier.model_dump(mode="json"),
                "partial",
                providers(),
            )
        if compose:
            await self.compose(dossier, scope.boundary, infer, providers)
        return await self.read(universe, continuity, arc, boundary)

    async def compose(
        self,
        dossier: ArcDossier,
        boundary_key: str,
        infer: Infer,
        providers: Callable[[], list[dict[str, Any]]],
    ) -> None:
        sections = []
        for section in dossier.sections:
            if not section.developments:
                continue
            section_id = section.id
            async with self.presentations() as repo:
                stored = await repo.get(self.identifier(section_id, "arc_section", boundary_key))
            if stored and stored["knowledge_revision"] == section.revision:
                sections.append(stored["payload"])
                continue
            selected = {i for b in section.developments for i in b.fact_ids}
            facts = [f for f in dossier.accepted_facts if f["id"] in selected]
            offset = len(providers())
            try:
                draft = ArcSectionDraft.model_validate(
                    await infer(
                        "Write original, connected encyclopedia prose for this arc section "
                        "using ONLY "
                        "the licensed assertion descriptions/atomic statements, never "
                        "additional clauses "
                        "from supporting quotations. Explain circumstances, choices, "
                        "conflict and consequences "
                        "only when supported. Preserve unknown transitions. No invented "
                        "motives, chronology "
                        "or causality. No author-memory additions. Each paragraph cites "
                        "exact fact_ids. "
                        "Develop substantial paragraphs if evidence supports them; sparse "
                        "evidence warrants "
                        "a short partial section, never padding. Do not copy source prose.\n"
                        + json.dumps(
                            {
                                "section": section.model_dump(mode="json"),
                                "facts": licensed_context(facts),
                            },
                            ensure_ascii=False,
                        ),
                        ArcSectionDraft,
                        "presentation",
                    )
                )
                references = {str(i + 1): f["id"] for i, f in enumerate(facts)}
                for paragraph in draft.paragraphs:
                    paragraph.fact_ids = [references.get(i, i) for i in paragraph.fact_ids]
                if any(not set(p.fact_ids) <= selected for p in draft.paragraphs):
                    raise ValueError("Unlicensed article citations")
                by_id = {f["id"]: f for f in facts}
                for paragraph in draft.paragraphs:
                    cited_types = {by_id[i]["payload"].get("type") for i in paragraph.fact_ids}
                    if re.search(
                        r"\b(because|therefore|caused|as a result|led to)\b", paragraph.text, re.I
                    ) and not cited_types & {"CAUSED", "ENABLED"}:
                        raise ValueError("Article causal bridge lacks an accepted causal assertion")
                assessment = GroundingAssessment.model_validate(
                    await infer(
                        "Verify every assertion in the original prose against ONLY licensed"
                        " canonical "
                        "assertions, not additional source quotation clauses. Check each "
                        "paragraph's own "
                        "citations. Reject unsupported motives, causal/temporal bridges, "
                        "changed roles, "
                        "names, contradictions or adaptation mixing.\n"
                        + json.dumps(
                            {
                                "heading": draft.heading,
                                "paragraphs": [
                                    {
                                        "text": p.text,
                                        "cited_assertions": licensed_context(
                                            [by_id[i] for i in p.fact_ids]
                                        ),
                                    }
                                    for p in draft.paragraphs
                                ],
                            }
                        ),
                        GroundingAssessment,
                        "presentation_verification",
                    )
                )
                status = (
                    "validated"
                    if (
                        assessment.entailed
                        and assessment.english
                        and assessment.names_consistent
                        and assessment.agency_and_tense_preserved
                        and not assessment.unsupported_relationships
                    )
                    else "withheld"
                )
                payload = {
                    "id": str(section.id),
                    "heading": draft.heading,
                    "paragraphs": [p.model_dump() for p in draft.paragraphs]
                    if status == "validated"
                    else [],
                    "status": status,
                    "assessment": assessment.model_dump(),
                    "revision": section.revision,
                }
            except InferenceFailure as error:
                if "budget" in error.code:
                    break
                raise
            except ValueError:
                # A bad section cannot discard other validated partial sections.
                status = "withheld"
                payload = {
                    "id": str(section.id),
                    "heading": section.plan.title,
                    "paragraphs": [],
                    "status": status,
                    "revision": section.revision,
                    "assessment": {"reason": "Deterministic citation or causal gate failed"},
                }
            await self.save(
                dossier.universe_id,
                dossier.continuity_id,
                section_id,
                "arc_section",
                boundary_key,
                section.revision,
                payload,
                status,
                providers()[offset:],
            )
            sections.append(payload)
        article = ArcArticle(
            arc_id=dossier.arc_id,
            continuity_id=dossier.continuity_id,
            title=dossier.title,
            perspective=dossier.perspective,
            spoiler_position=dossier.spoiler_position,
            dossier_revision=dossier.revision,
            sections=sections,
            coverage=[s.coverage for s in dossier.sections],
            quality={
                "complete": False,
                "validated_sections": sum(s["status"] == "validated" for s in sections),
                "gate": "Requires real narrative review; generation success is not completeness",
            },
        )
        # Rendering is a projection, not a new canonical assertion.
        current = await self.read(
            dossier.universe_id, dossier.continuity_id, dossier.arc_id, dossier.spoiler_position
        )
        if current["dossier"] and current["dossier"]["revision"] == dossier.revision:
            await self.save(
                dossier.universe_id,
                dossier.continuity_id,
                dossier.arc_id,
                "arc_article",
                boundary_key,
                dossier.revision,
                article.model_dump(mode="json"),
                "partial",
                providers(),
            )


def article_markdown(result: dict[str, Any]) -> str:
    """Export exact published paragraphs with source references, never fill gaps."""
    article, dossier = result.get("article"), result.get("dossier")
    if not article or not dossier:
        return "# Arc article unavailable\n\nNo current validated article artifact.\n"
    facts = {f["id"]: f for f in dossier["accepted_facts"]}
    lines = [
        f"# {article['title']}",
        "",
        "Status: partial; coverage is assessed separately from prose validation.",
        "",
    ]
    for section in article["sections"]:
        if section["status"] != "validated":
            continue
        lines += [f"## {section['heading']}", ""]
        for paragraph in section["paragraphs"]:
            refs = sorted(
                {
                    (s["url"], s.get("locator", ""))
                    for i in paragraph["fact_ids"]
                    for s in facts[i]["sources"]
                }
            )
            lines += [
                paragraph["text"],
                "",
                "Sources: " + "; ".join(f"[{loc or 'evidence'}]({url})" for url, loc in refs),
                "",
            ]
    lines += ["## Coverage and unfinished research", ""]
    for section in dossier["sections"]:
        lines += [
            f"### {section['plan']['title']}",
            f"Research: {section['coverage']['research']}.",
            *[f"- {g}" for g in section["coverage"]["gaps"]],
            "",
        ]
    return "\n".join(lines)
