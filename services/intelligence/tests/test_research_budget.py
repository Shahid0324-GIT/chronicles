import pytest

from src.application.research_budget import budget_ledger, reserve_inference
from src.application.research_contracts import InferenceFailure
from src.application.research_policy import ResearchPolicy


def test_protected_allowance_and_unknown_reservations_survive_accounting():
    policy = ResearchPolicy(max_model_calls=10, max_tokens=10000, verification_reserve_fraction=0.4)
    events = [
        {
            "stage": "inference.started",
            "detail": {"task": "extraction", "reservation_id": "a", "reserved_tokens": 5000},
        },
        {
            "stage": "inference.started",
            "detail": {"task": "extraction", "reservation_id": "b", "reserved_tokens": 2000},
        },
    ]
    usage = [{"reservation_id": "a", "input_tokens": 2500, "output_tokens": 1000}]
    ledger = budget_ledger(events, usage)
    assert ledger["extraction"] == {"calls": 2, "tokens": 5500, "incomplete": 1}
    with pytest.raises(InferenceFailure, match="verification_reserve_budget_exhausted"):
        reserve_inference(policy, ledger, "extraction", 1000, 10)
    reserve_inference(policy, ledger, "verification", 3000, 10)
    with pytest.raises(InferenceFailure, match="job_token_budget_exhausted"):
        reserve_inference(policy, ledger, "verification", 5000, 10)
    # A restart uses the same ledger, not a replenished allowance.
    assert budget_ledger(events, usage) == ledger


def test_verification_call_allowance_is_protected_from_routine_stage_work():
    policy = ResearchPolicy(
        max_model_calls=10, max_tokens=100000, verification_reserve_fraction=0.4
    )
    stages = {"extraction": {"calls": 6, "tokens": 100, "incomplete": 0}}
    with pytest.raises(InferenceFailure, match="verification_reserve_budget_exhausted"):
        reserve_inference(policy, stages, "identity_resolution", 100, 10)
    reserve_inference(policy, stages, "verification", 100, 10)
