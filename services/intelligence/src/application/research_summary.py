from datetime import datetime
from typing import Any


def research_summary(
    job: dict[str, Any], findings: list[dict[str, Any]], events: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    usage = job["provider_usage"]
    calls = [u for u in usage if u.get("model_call", u["status"] != "cache_hit")]
    state = job["checkpoint"]
    active = [f for f in findings if f["canonical"]]
    closed = {u.get("reservation_id") for u in usage}
    pending = [
        e
        for e in (events or [])
        if e["stage"] == "inference.started" and e["detail"]["reservation_id"] not in closed
    ]
    discoveries: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in active:
        if state.get("resolutions", {}).get(finding["id"], {}).get("hidden_identity"):
            continue
        payload = finding["payload"]
        label = payload.get("name") or (
            f"{payload.get('source_name', '')} → {payload.get('target_name', '')} · "
            + str(payload.get("type", "relationship")).lower().replace("_", " ")
        )
        discoveries.setdefault(
            (finding["kind"], finding["canonical_id"]),
            {
                "id": finding["id"],
                "canonical_id": finding["canonical_id"],
                "kind": finding["kind"],
                "type": payload.get("type"),
                "label": label,
            },
        )
    return {
        "id": job["id"],
        "status": job["status"],
        "stage": state.get("active_stage") or state.get("stage", "queued"),
        "error": job["error"],
        "model_calls": len(calls) + len(pending),
        "incomplete_call_reservations": len(pending),
        "cache_hits": sum(u["status"] == "cache_hit" for u in usage),
        "retry_count": sum(u.get("retry", 0) > 0 for u in calls),
        "validation_failures": sum(u["status"] == "invalid_output" for u in calls),
        "providers": sorted({u["provider"] + ":" + u["model"] for u in usage}),
        "sources": len(state.get("source_ids", [])),
        "source_retrievals": state.get("source_retrievals", 0),
        "embedding_reused": state.get("indexing", {}).get("reused", 0),
        "embedding_generated": state.get("indexing", {}).get("indexed", 0),
        "candidate_entities": sum(f["kind"] == "entity" for f in findings),
        "accepted_relationships": len(
            {f["canonical_id"] for f in active if f["kind"] == "relationship"}
        ),
        "unresolved_findings": len(findings) - len(active),
        "elapsed_ms": int(
            (
                datetime.fromisoformat(job["updated_at"])
                - datetime.fromisoformat(job["created_at"])
            ).total_seconds()
            * 1000
        ),
        "stage_elapsed_ms": state.get("telemetry", {}).get("stages", {}),
        "discoveries": list(discoveries.values()),
    }
