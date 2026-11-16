"""Token-aware connected evidence selection over currently eligible archived passages."""

import json
import re
from uuid import UUID, uuid5

from src.application.evidence_dossier import token_estimate
from src.application.ports.retrieval import EvidenceHit
from src.application.relationship_contracts import (
    BundlePassage,
    EvidenceBundle,
    InvestigationSubject,
)
from src.application.research_frontier import terms
from src.domain.knowledge import name_key
from src.domain.research import digest


def connection_score(text: str, subjects: list[InvestigationSubject], objective: str) -> float:
    value = name_key(text)
    coverage = sum(
        any(name_key(n) in value for n in [subject.name, *subject.aliases]) for subject in subjects
    )
    actions = len(
        re.findall(
            r"\b(helped|assisted|rescued|saved|invented|developed|created|became|consulting|"
            r"collaborated|joined|taught|trained|saves|rescues|helps|gives|gave|recruits|"
            r"recruited|recruiting|joins|eats|ate|receives|received|defeats|fights|fought)\b"
            r"|助け|救っ|発明|協力|同行",
            text,
            re.I,
        )
    )
    production = bool(re.search(r"\bI (?:am |was )?(?:writing|working on|wrote)\b", text, re.I))
    overlap = len(terms(objective) & terms(text)) / max(1, len(terms(text)))
    return coverage * 16 + min(actions, 4) * 8 + overlap * 8 - production * 24


class EvidenceBundleBuilder:
    def build(
        self,
        hits: list[EvidenceHit],
        subjects: list[InvestigationSubject],
        objective: str,
        continuity: UUID,
        spoiler_position: int | None,
        token_budget: int,
    ) -> list[EvidenceBundle]:
        eligible = [
            h
            for h in hits
            if h.source.continuity_id == continuity
            and (
                spoiler_position is None
                or isinstance(h.source.provenance.get("presentation_position"), int)
                and h.source.provenance["presentation_position"] <= spoiler_position
            )
        ]
        ranked = sorted(
            eligible,
            key=lambda h: (
                -connection_score(h.passage.text, subjects, objective),
                str(h.passage.id),
            ),
        )
        bundles: list[EvidenceBundle] = []
        used = 0
        represented: set[UUID] = set()
        for hit in ranked:
            if hit.passage.id in represented or not any(
                name_key(n) in name_key(hit.passage.text)
                for subject in subjects
                for n in [subject.name, *subject.aliases]
            ):
                continue
            # Neighbors share the exact explicit section; do not cross adaptation labels.
            context = [
                h
                for h in eligible
                if h.source.id == hit.source.id
                and h.passage.section_title == hit.passage.section_title
                and abs(h.passage.ordinal - hit.passage.ordinal) <= 1
            ]
            context.sort(key=lambda h: (h.passage.id != hit.passage.id, h.passage.ordinal))
            refs: list[BundlePassage] = []
            cost = 0
            hashes: set[str] = set()
            for h in context:
                if h.passage.content_hash in hashes:
                    continue
                size = token_estimate(h.passage.text)
                if used + cost + size > token_budget:
                    continue
                refs.append(
                    BundlePassage(
                        passage_id=h.passage.id,
                        source_id=h.source.id,
                        source_revision=h.source.content_hash,
                        passage_hash=h.passage.content_hash,
                        start=h.passage.start,
                        end=h.passage.end,
                        text=h.passage.text,
                        section=h.passage.section_title,
                        url=h.source.url,
                        authority=h.source.provenance.get("authority", "unverified"),
                        source_family=h.source.independence_key or h.source.publisher,
                        language=h.source.provenance.get("language", "und"),
                        cloud_allowed=bool(
                            h.source.public_web and h.source.provenance.get("cloud_content_allowed")
                        ),
                    )
                )
                cost += size
                hashes.add(h.passage.content_hash)
            if not refs or refs[0].passage_id != hit.passage.id:
                continue
            permissions = digest(
                json.dumps(
                    [[str(h.source.id), h.source.provenance] for h in context],
                    sort_keys=True,
                    default=str,
                )
            )
            fingerprint = digest(
                json.dumps(
                    {
                        "policy": "relationship-bundles-v2",
                        "continuity": str(continuity),
                        "boundary": spoiler_position,
                        "permissions": permissions,
                        "subjects": [
                            s.model_dump(mode="json", exclude={"canonical_id"}) for s in subjects
                        ],
                        "passages": [r.model_dump(mode="json") for r in refs],
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
            bundles.append(
                EvidenceBundle(
                    id=uuid5(continuity, fingerprint),
                    fingerprint=fingerprint,
                    continuity_id=continuity,
                    spoiler_position=spoiler_position,
                    subjects=subjects,
                    passages=refs,
                    anchor_passage_id=hit.passage.id,
                    score=connection_score(hit.passage.text, subjects, objective),
                    estimated_tokens=cost,
                    permission_fingerprint=permissions,
                )
            )
            used += cost
            represented.update(r.passage_id for r in refs)
        return bundles
