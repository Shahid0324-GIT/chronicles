"""Durable arc research projections over the existing canonical evidence graph.

Model assignments are editorial organization only. They cannot add canonical
assertions. Prose has an independent artifact and grounding gate.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel

from src.application.arc_contracts import (
    ArcArticle,
    ArcDossier,
)
from src.application.arc_understanding import build_arc_understanding, write_arc_article
from src.application.connector_lint import LINKING_TYPES
from src.application.knowledge_presentation import Infer, KnowledgeAtlas, fingerprint
from src.application.ports.presentation import PresentationTransaction
from src.application.ports.retrieval import DevelopmentEvidenceProvider
from src.application.research_contracts import InferenceFailure, Task
from src.application.story_bible import build_story_bible

POLICY = "arc-intelligence-v30"
ORGANIZATION_POLICY = "arc-intelligence-v9"


class ArcIntelligence:
    def __init__(
        self,
        atlas: KnowledgeAtlas,
        presentations: PresentationTransaction,
        evidence: DevelopmentEvidenceProvider | None = None,
    ) -> None:
        self.atlas, self.presentations, self.evidence = atlas, presentations, evidence

    @staticmethod
    def artifact_policy(kind: str) -> str:
        if kind == "arc_plan":
            return "arc-intelligence-v2"
        if kind == "arc_development_plan":
            return "development-plan-v3"
        if kind in {"arc_reconstruction", "arc_prose_batches"}:
            return "arc-intelligence-v29"
        return ORGANIZATION_POLICY if kind == "arc_dossier" else POLICY

    @staticmethod
    def identifier(arc: UUID, kind: str, boundary: str) -> UUID:
        return uuid5(arc, f"{ArcIntelligence.artifact_policy(kind)}:{kind}:{boundary}")

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
        unique = {}
        for fact in facts:
            if fact["target_id"] not in eligible:
                continue
            value = {k: v for k, v in fact.items() if k != "id"}
            value["payload"] = {k: v for k, v in fact["payload"].items() if k != "evidence"}
            value["sources"] = [
                {
                    **s,
                    "provenance": {
                        k: v for k, v in s.get("provenance", {}).items() if k != "job_id"
                    },
                }
                for s in fact["sources"]
            ]
            key = fingerprint(value)
            unique[key] = {**value, "id": key}
        selected = [unique[key] for key in sorted(unique)]
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
        evidence_revision: str | None = None,
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
                evidence_revision or revision,
                "en",
                self.artifact_policy(kind),
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
            [
                facts,
                definition.model_dump(mode="json"),
                scope.knowledge.reference_outline,
                (stored or {}).get("payload", {}).get("section_focus", []),
            ]
        )
        if not stored or stored["evidence_fingerprint"] != current:
            return {
                "status": "pending",
                "reason": "Current evidence has no matching dossier",
                "dossier": None,
                "article": None,
            }
        dossier = ArcDossier.model_validate(stored["payload"])
        if allowed_sources is not None:
            catalog = await self.atlas.catalog(
                universe, continuity, allowed_sources=allowed_sources, spoiler_position=boundary
            )
            dossier.reconstruction = next(
                (r for r in catalog.get("reconstructions", []) if r["arcId"] == str(arc)), {}
            )
        article_payload = (
            dict(article["payload"])
            if article and article["knowledge_revision"] == dossier.revision
            else None
        )
        if article_payload and not any(
            s["status"] == "validated" for s in article_payload.get("sections", [])
        ):
            article_payload["status"] = "withheld"
        if article_payload:
            for section in dossier.sections:
                presentation = next(
                    (
                        s
                        for s in article_payload.get("sections", [])
                        if s["id"] == str(section.id) and s.get("revision") == section.revision
                    ),
                    None,
                )
                if presentation and presentation["status"] in {"validated", "withheld"}:
                    section.coverage.presentation = presentation["status"]
            article_payload["coverage"] = [s.coverage.model_dump() for s in dossier.sections]
        return {
            "status": "partial",
            "dossier": dossier.model_dump(mode="json"),
            "article": article_payload,
        }

    async def rebuild_understanding(
        self,
        universe: UUID,
        continuity: UUID,
        arc: UUID,
        boundary: int | None,
        infer: Infer,
        providers: Callable[[], list[dict[str, Any]]],
        *,
        compose: bool = True,
        survey_only: bool = False,
        allowed_sources: list[UUID] | None = None,
    ) -> dict[str, Any]:
        scope, definition, facts = await self.context(
            universe, continuity, arc, boundary, allowed_sources
        )
        ceiling = (
            definition.last_position
            if boundary is None
            else min(boundary, definition.last_position)
        )
        evidence_revision = fingerprint(
            [
                facts,
                definition.model_dump(mode="json"),
                scope.knowledge.reference_outline,
                [],
            ]
        )
        source_range = (definition.first_position, ceiling)
        if survey_only:
            async with self.presentations() as repo:
                cached = await repo.get(self.identifier(arc, "arc_dossier", scope.boundary))
            account = (
                cached["payload"].get("understanding")
                if cached and cached["evidence_fingerprint"] == evidence_revision
                else None
            )
            questions = (
                account["coverage"]["search_questions"]
                if account
                else [
                    f"What are the main conflicts, turning points and resolution of "
                    f"{definition.title} in {definition.position_basis} positions "
                    f"{source_range[0]}–{source_range[1]}?"
                ]
            )
            return {
                "survey": {
                    "title": definition.title,
                    "source_range": source_range,
                    "position_basis": definition.position_basis,
                    "accepted_assertions": len(facts),
                    "questions": questions,
                    "understanding_status": account["status"] if account else None,
                    "fact_ids": sorted({i for p in account["paragraphs"] for i in p["fact_ids"]})
                    if account
                    else [],
                    "evidence_revision": evidence_revision,
                }
            }
        if self.evidence is None:
            raise ValueError("Arc understanding requires inspectable archive evidence")
        units, evidence_issues = await self.evidence.development_evidence(
            universe,
            continuity,
            facts,
            boundary,
        )
        dossier = ArcDossier(
            arc_id=arc,
            universe_id=universe,
            continuity_id=continuity,
            title=definition.title,
            perspective="bounded" if boundary is not None else "full_lore",
            spoiler_position=boundary,
            source_range=source_range,
            accepted_facts=facts,
            bible=build_story_bible(scope.knowledge.nodes, facts, boundary),
            ordering_links=[
                (str(e.source_node_id), str(e.target_node_id))
                for e in scope.edges()
                if e.relationship_type.value in LINKING_TYPES
            ],
            sections=[],
            reconstruction={},
            organization_warnings=evidence_issues,
            revision=evidence_revision,
        )

        async def checkpointed(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
            key = fingerprint(["holistic-arc-v1", task, schema.model_json_schema(), prompt])
            resource = uuid5(arc, key)
            kind = f"arc_understanding_{schema.__name__}"
            async with self.presentations() as repo:
                saved = await repo.get(self.identifier(resource, kind, scope.boundary))
            if saved:
                return schema.model_validate(saved["payload"])
            start = len(providers())
            value = await infer(prompt, schema, task)
            await self.save(
                universe,
                continuity,
                resource,
                kind,
                scope.boundary,
                key,
                value.model_dump(mode="json"),
                "withheld",
                providers()[start:],
            )
            return value

        async def persist_dossier() -> None:
            current_scope, current_definition, current_facts = await self.context(
                universe,
                continuity,
                arc,
                boundary,
                allowed_sources,
            )
            if (
                fingerprint(
                    [
                        current_facts,
                        current_definition.model_dump(mode="json"),
                        current_scope.knowledge.reference_outline,
                        [],
                    ]
                )
                != evidence_revision
            ):
                raise ValueError("Evidence changed during arc understanding")
            await self.save(
                universe,
                continuity,
                arc,
                "arc_dossier",
                scope.boundary,
                dossier.revision,
                dossier.model_dump(mode="json"),
                "partial",
                providers(),
                evidence_revision=evidence_revision,
            )

        dossier.understanding = await build_arc_understanding(dossier, units, checkpointed)
        dossier.revision = fingerprint([evidence_revision, dossier.understanding])
        await persist_dossier()
        if compose:
            article = ArcArticle(
                arc_id=arc,
                continuity_id=continuity,
                title=definition.title,
                perspective=dossier.perspective,
                spoiler_position=boundary,
                dossier_revision=dossier.revision,
                status="withheld",
                sections=[],
                coverage=[],
                quality={
                    "complete": False,
                    "validated_sections": 0,
                    "reason": "arc_understanding_incomplete",
                },
            )
            if dossier.understanding.status == "qualified":
                try:
                    article = await write_arc_article(
                        dossier,
                        dossier.understanding,
                        units,
                        checkpointed,
                        identifier=lambda key: uuid5(arc, key),
                    )
                except ValueError as error:
                    article.quality["reason"] = str(error)
                except InferenceFailure as error:
                    if error.code != "structured_output_exhausted":
                        raise
                    article.quality["reason"] = error.code
                await persist_dossier()
            await self.save(
                universe,
                continuity,
                arc,
                "arc_article",
                scope.boundary,
                dossier.revision,
                article.model_dump(mode="json"),
                article.status,
                providers(),
            )
        return await self.read(universe, continuity, arc, boundary, allowed_sources)

    @staticmethod
    def research_questions(dossier: dict[str, Any], section_keys: list[str]) -> list[str]:
        """Keep story evidence gaps separate from errors processing an existing assertion."""
        if dossier.get("understanding") is not None:
            return list(dossier["understanding"]["coverage"]["search_questions"])
        questions: list[str] = []
        for section in dossier.get("sections", []):
            scope = section["plan"]
            if section_keys and scope["key"] not in section_keys:
                continue
            plan = section.get("development_plan")
            if not plan:
                # An invalid proposal is not evidence of missing story material.
                if dossier.get("accepted_facts"):
                    continue
                gaps = scope["questions"]
            elif plan["factual"]["status"] == "passed" and plan["structural"]["status"] == "passed":
                gaps = plan.get("evidence_questions", [])
            else:
                continue
            questions.extend(
                f"{scope['title']} — {gap.strip()}" for gap in gaps if gap.strip().endswith("?")
            )
        return list(dict.fromkeys(questions))


def article_markdown(result: dict[str, Any]) -> str:
    """Export exact published paragraphs with source references, never fill gaps."""
    article, dossier = result.get("article"), result.get("dossier")
    if not article or not dossier:
        return "# Arc article unavailable\n\nNo current validated article artifact.\n"
    facts = {f["id"]: f for f in dossier["accepted_facts"]}
    lines = [
        f"# {article['title']}",
        "",
        "Status: validated complete article."
        if article["quality"].get("complete")
        else "Status: partial; coverage is assessed separately from prose validation.",
        "",
    ]
    if dossier.get("claims_origin") == "controlled_reference_dossier":
        lines += [
            "Controlled reconstruction from the fixed reference dossier.",
            "",
        ]
    if article["status"] == "withheld":
        lines += [
            "Article quality gate: FAILED. No validated narrative paragraphs are available.",
            "",
        ]
    notes: list[str] = []
    for section in article["sections"]:
        if section["status"] != "validated":
            continue
        lines += [f"## {section['heading']}", ""]
        for paragraph in section["paragraphs"]:
            cited = []
            for claim in paragraph["claims"]:
                number = len(notes) + 1
                refs = sorted(
                    {
                        (s["url"], s.get("title") or "Archived evidence")
                        for i in claim["fact_ids"]
                        for s in facts[i]["sources"]
                    }
                )
                context = [
                    f"Archived passage `{u['passage_id']}`, offsets {u['start']}–{u['end']}"
                    for s in dossier["sections"]
                    for u in (s.get("development_plan") or {}).get("evidence", [])
                    if u["id"] in claim.get("context_evidence_ids", [])
                ]
                cited.append(f"{claim['text']}[^{number}]")
                notes.append(
                    f"[^{number}]: "
                    + ", ".join([*(f"[{title}]({url})" for url, title in refs), *context])
                )
            lines += [" ".join(cited), ""]
    if notes:
        lines += ["## Source references", "", *notes, ""]
    lines += ["## Coverage and unfinished research", ""]
    for section in dossier["sections"]:
        lines += [
            f"### {section['plan']['title']}",
            f"Research: {section['coverage']['research']}.",
            *[f"- {g}" for g in section["coverage"]["gaps"]],
            "",
        ]
    return "\n".join(lines)


def understanding_markdown(dossier: dict[str, Any]) -> str:
    """Render the stored model output verbatim with traceable archived citations."""
    document = dossier["understanding"]
    facts = {f["id"]: f for f in dossier["accepted_facts"]}
    lines = [
        f"# {document['title']} · Arc Understanding Document",
        "",
        f"Grounding status: **{document['status'].replace('_', ' ')}**. "
        f"Withheld generated paragraphs: {document['withheld_paragraphs']}.",
        "",
    ]
    notes: list[str] = []
    for paragraph in document["paragraphs"]:
        claims = []
        for claim in paragraph["claims"]:
            refs = []
            for fact_id in claim["fact_ids"]:
                for source in facts[fact_id]["sources"]:
                    where = source.get("locator") or "archived passage"
                    refs.append(
                        f"[{source.get('title') or 'Source'}]({source['url']}) "
                        f"({where}, assertion `{fact_id[:12]}`)"
                    )
            number = len(notes) + 1
            notes.append(f"[^{number}]: " + " · ".join(dict.fromkeys(refs)))
            claims.append(f"{claim['text']}[^{number}]")
        lines.extend([" ".join(claims), ""])
    if not document["paragraphs"]:
        lines.extend(["The account has no paragraphs that passed grounding.", ""])
    if document["gaps"] or document["coverage"]["issues"]:
        lines.extend(["## Unfinished coverage", ""])
        lines.extend(f"- {g['question']} ({g['kind'].replace('_', ' ')})" for g in document["gaps"])
        lines.extend(f"- {issue}" for issue in document["coverage"]["issues"])
        lines.append("")
    if notes:
        lines.extend(["## Archived references", "", *notes, ""])
    return "\n".join(lines)
