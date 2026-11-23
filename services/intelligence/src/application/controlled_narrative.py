"""Fixed permitted evidence input for the SAME arc services; no acquisition or canon writes."""

from typing import Any
from uuid import UUID

from src.application.arc_contracts import DevelopmentEvidence
from src.application.evidence_dossier import token_estimate
from src.application.knowledge_presentation import fingerprint


class FixedDevelopmentEvidence:
    def __init__(self, universe: UUID, continuity: UUID, units: list[DevelopmentEvidence]) -> None:
        self.universe, self.continuity = universe, continuity
        self.units = tuple(u.model_copy(deep=True) for u in units)
        self.revision = fingerprint([u.model_dump(mode="json") for u in self.units])

    async def development_evidence(
        self,
        universe: UUID,
        continuity: UUID,
        facts: list[dict[str, Any]],
        spoiler_position: int | None,
        token_budget: int = 3200,
    ) -> tuple[list[DevelopmentEvidence], list[str]]:
        if (universe, continuity) != (self.universe, self.continuity):
            return [], ["Fixed dossier continuity mismatch"]
        if any(
            spoiler_position is not None
            and (u.eligibility_boundary is None or u.eligibility_boundary > spoiler_position)
            for u in self.units
        ):
            return [], ["Fixed dossier exceeds reader boundary"]
        if sum(token_estimate(u.text) for u in self.units) > token_budget:
            return [], ["Complete fixed dossier exceeds context budget; do not silently truncate"]
        return [u.model_copy(deep=True) for u in self.units], []


def reference_assertions(
    units: list[DevelopmentEvidence], source_urls: dict[str, str]
) -> list[dict[str, Any]]:
    """Quote-backed premises for controlled reconstruction, explicitly NOT canonical nodes."""
    return [
        {
            "id": u.id,
            "target_id": str(u.source_id),
            "kind": "controlled_reference_assertion",
            "evidence_status": "reference_only_not_canonical",
            "payload": {"description": u.text, "type": "DOCUMENT"},
            "sources": [
                {
                    "id": str(u.source_id),
                    "url": source_urls[str(u.source_id)],
                    "title": "Frozen permitted reference evidence",
                    "passage_id": str(u.passage_id),
                    "content_hash": u.source_hash,
                    "quote": u.text,
                    "quote_start": u.start - u.passage_start,
                    "quote_end": u.end - u.passage_start,
                    "provenance": {
                        "presentation_position": u.eligibility_boundary,
                        "position_basis": u.position_basis,
                    },
                }
            ],
        }
        for u in units
    ]
