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

    @staticmethod
    def rank(leads: list[ResearchLead], objective: str) -> list[ResearchLead]:
        """Prefer missing connections with evidence over repeatedly unanswered trivia."""

        def value(lead: ResearchLead) -> float:
            words = terms(lead.question)
            connection = bool(
                words
                & {
                    "meet",
                    "met",
                    "recruit",
                    "recruitment",
                    "joined",
                    "joins",
                    "rescued",
                    "rescue",
                    "relationship",
                    "interactions",
                    "conflict",
                    "connections",
                }
            )
            detail = bool(words & {"spelling", "romanization", "alias", "aliases"})
            available = min(2, len(lead.source_ids)) * 8 + min(2, len(lead.available_sources)) * 2
            relevance = min(10, len(words & terms(objective)))
            return (
                (lead.priority + connection * 20 - detail * 12 + available + relevance)
                * lead.expected_value
                / max(1, lead.estimated_cost)
                / (1 + 0.25 * lead.attempt_count)
            )

        return sorted(
            leads, key=lambda lead: (lead.status == "RESOLVED", -value(lead), str(lead.id))
        )

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
            for question in list(dict.fromkeys(questions))[: policy.max_leads]:
                key = digest(" ".join(question.casefold().split()))
                identifier = uuid5(continuity, boundary + objective_key + key)
                if any(lead.id == identifier for lead in existing):
                    continue
                query_terms = terms(question)
                similar = next(
                    (
                        lead
                        for lead in existing
                        if lead.objective_key == objective_key
                        and len(query_terms & terms(lead.question))
                        / max(1, len(query_terms | terms(lead.question)))
                        > 0.8
                    ),
                    None,
                )
                if similar:
                    if question not in similar.related_questions:
                        similar.related_questions.append(question)
                        await memory.save_lead(similar)
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
        return self.rank(
            [lead for lead in existing if lead.objective_key == objective_key],
            objective,
        )
