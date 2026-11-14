"""Persistent questions, independent of a job's lifetime or model budget."""

import re
from uuid import UUID, uuid5

from src.application.ports.frontier import ResearchMemoryTransaction
from src.application.research_policy import ResearchLead, ResearchPolicy
from src.domain.research import digest


def terms(text: str) -> set[str]:
    stop = {"the", "and", "what", "with", "from", "this", "that", "which", "about", "does", "into"}
    return {
        w
        for w in re.findall(r"\w+", text.casefold())
        if (len(w) > 2 or (len(w) > 1 and not w.isascii())) and w not in stop
    }


class ResearchFrontierService:
    def __init__(self, transactions: ResearchMemoryTransaction) -> None:
        self.transactions = transactions

    @staticmethod
    def boundary(position: int | None) -> str:
        return digest(str(position))

    async def discover(
        self,
        universe: UUID,
        continuity: UUID,
        position: int | None,
        objective: str,
        questions: list[str],
        origin: str,
        policy: ResearchPolicy,
        *,
        depth: int = 0,
    ) -> list[ResearchLead]:
        boundary = self.boundary(position)
        objective_key = digest(" ".join(objective.casefold().split()))
        async with self.transactions() as memory:
            existing = await memory.leads(universe, continuity, boundary)
            if depth <= policy.max_follow_up_depth:
                for question in list(dict.fromkeys(questions))[: policy.max_leads]:
                    key = digest(" ".join(question.casefold().split()))
                    identifier = uuid5(continuity, boundary + objective_key + key)
                    if any(lead.id == identifier for lead in existing):
                        continue
                    overlap = len(terms(question) & terms(objective))
                    lead = ResearchLead(
                        id=identifier,
                        universe_id=universe,
                        continuity_id=continuity,
                        boundary_key=boundary,
                        objective_key=objective_key,
                        question=question,
                        topic=objective[:300],
                        discovery_origin=origin,
                        depth=depth,
                        priority=min(100, 50 + overlap * 5),
                        missing_evidence=["Source-backed answer not yet established"],
                    )
                    existing.append(await memory.save_lead(lead))
        return sorted(
            [lead for lead in existing if lead.objective_key == objective_key],
            key=lambda lead: (
                -lead.priority * lead.expected_value / max(1, lead.estimated_cost),
                str(lead.id),
            ),
        )
