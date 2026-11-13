export interface ResearchSummary {
  id: string;
  status:
    "queued" | "running" | "completed" | "partial" | "failed" | "cancelled";
  stage: string;
  error: string | null;
  model_calls: number;
  cache_hits: number;
  retry_count: number;
  validation_failures: number;
  sources: number;
  embedding_reused: number;
  accepted_relationships: number;
  unresolved_findings: number;
  discoveries: {
    id: string;
    canonical_id: string;
    kind: string;
    type: string;
    label: string;
  }[];
}
export const terminal = (status: ResearchSummary["status"]) =>
  status !== "queued" && status !== "running";
export async function startResearch(
  universe: string,
  continuity: string,
  objective: string,
  position?: number,
): Promise<string> {
  const response = await fetch("/api/atlas/research/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      universe_id: universe,
      continuity_id: continuity,
      objective,
      spoiler_position: position,
    }),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok)
    throw new Error(
      "Research could not be queued. Check the local service and source registry.",
    );
  const value: unknown = await response.json();
  if (
    !value ||
    typeof value !== "object" ||
    !("id" in value) ||
    typeof value.id !== "string" ||
    !/^[0-9a-f-]{36}$/i.test(value.id)
  )
    throw new Error("Invalid research response.");
  return value.id;
}
export async function getResearchSummary(
  id: string,
  signal?: AbortSignal,
): Promise<ResearchSummary> {
  const response = await fetch(
    `/api/atlas/research/jobs/${encodeURIComponent(id)}/summary`,
    { cache: "no-store", signal },
  );
  if (!response.ok)
    throw new Error("Research status is temporarily unavailable.");
  const v = await response.json();
  if (
    !v ||
    v.id !== id ||
    ![
      "queued",
      "running",
      "completed",
      "partial",
      "failed",
      "cancelled",
    ].includes(v.status) ||
    typeof v.stage !== "string" ||
    !(v.error === null || typeof v.error === "string") ||
    ![
      "model_calls",
      "cache_hits",
      "retry_count",
      "validation_failures",
      "sources",
      "embedding_reused",
      "accepted_relationships",
      "unresolved_findings",
    ].every((k) => Number.isInteger(v[k]) && v[k] >= 0) ||
    !Array.isArray(v.discoveries) ||
    !v.discoveries.every(
      (d: Record<string, unknown>) =>
        typeof d.label === "string" &&
        typeof d.canonical_id === "string" &&
        typeof d.id === "string",
    )
  )
    throw new Error("Invalid research status response.");
  return v as ResearchSummary;
}
