"""Persisted usage accounting and a protected verification allowance; no budget resets."""

from typing import Any

from src.application.research_contracts import InferenceFailure
from src.application.research_policy import ResearchPolicy

PROTECTED_TASKS = {"verification", "presentation", "presentation_verification"}


def budget_ledger(
    events: list[dict[str, Any]], usage: list[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    completed = {u.get("reservation_id"): u for u in usage if u.get("reservation_id")}
    stages: dict[str, dict[str, int]] = {}
    for event in events:
        if event["stage"] != "inference.started":
            continue
        detail = event["detail"]
        measured = completed.get(detail["reservation_id"], {})
        tokens = int(measured.get("input_tokens", 0)) + int(measured.get("output_tokens", 0))
        row = stages.setdefault(detail["task"], {"calls": 0, "tokens": 0, "incomplete": 0})
        row["calls"] += 1
        row["tokens"] += tokens if tokens > 0 else int(detail.get("reserved_tokens", 0))
        row["incomplete"] += int(not measured or tokens <= 0)
    return stages


def reserve_inference(
    policy: ResearchPolicy,
    stages: dict[str, dict[str, int]],
    task: str,
    tokens: int,
    max_calls: int,
) -> None:
    charged = sum(row["tokens"] for row in stages.values())
    calls = sum(row["calls"] for row in stages.values())
    if charged + tokens > policy.max_tokens:
        raise InferenceFailure("job_token_budget_exhausted")
    if calls >= min(policy.max_model_calls, max_calls):
        raise InferenceFailure("job_model_budget_exhausted")
    if task not in PROTECTED_TASKS:
        fraction = 1 - policy.verification_reserve_fraction
        spent = sum(row["tokens"] for name, row in stages.items() if name not in PROTECTED_TASKS)
        spent_calls = sum(
            row["calls"] for name, row in stages.items() if name not in PROTECTED_TASKS
        )
        if spent + tokens > int(policy.max_tokens * fraction) or spent_calls >= int(
            min(policy.max_model_calls, max_calls) * fraction
        ):
            raise InferenceFailure("verification_reserve_budget_exhausted")
