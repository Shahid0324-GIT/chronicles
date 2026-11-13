import type { UniverseGraph } from "@/lib/contracts";
import type { NarrativeCatalog, PresentationHint } from "./contracts";

/** Resolve references against the API graph; never manufacture missing entities or sequence steps. */
export function resolveNarrative(
  catalog: NarrativeCatalog,
  graph: UniverseGraph,
  continuityId: string | null,
) {
  const issues: string[] = [];
  const nodes = new Map(
    graph.nodes
      .filter(
        (n) =>
          n.universe_id === graph.universe.id &&
          (!n.continuity_id || n.continuity_id === continuityId),
      )
      .map((n) => [n.id, n]),
  );
  const edges = new Map(
    graph.edges
      .filter(
        (e) =>
          e.universe_id === graph.universe.id &&
          (!e.continuity_id || e.continuity_id === continuityId) &&
          nodes.has(e.source) &&
          nodes.has(e.target),
      )
      .map((e) => [e.id, e]),
  );
  const sources = new Set(
    catalog.sources
      .filter((s) => /^https?:\/\//.test(s.url) && s.locator.trim())
      .map((s) => s.id),
  );
  const sourced = (ids: string[]) =>
    ids.length > 0 && ids.every((id) => sources.has(id));
  const hintValid = (hint: PresentationHint) =>
    hint.relatedNodeIds.every((id) => nodes.has(id)) &&
    hint.relationshipIds.every((id) => edges.has(id)) &&
    (hint.focusRatio === undefined ||
      (Number.isFinite(hint.focusRatio) &&
        hint.focusRatio >= 0.25 &&
        hint.focusRatio <= 3));
  const scoped = (value: { universeId: string; continuityId: string }) =>
    value.universeId === graph.universe.id &&
    value.continuityId === continuityId;
  const journeys = catalog.journeys.filter((j) => {
    const valid =
      scoped(j) &&
      j.ordering.basis === "broadcast-presentation" &&
      sourced(j.ordering.sourceIds) &&
      j.steps.length >= 2 &&
      new Set(j.steps.map((s) => s.id)).size === j.steps.length &&
      j.steps.every(
        (s) =>
          nodes.get(s.eventNodeId)?.type === "EVENT" &&
          hintValid(s.presentation) &&
          sourced(s.sourceIds),
      );
    if (!valid) issues.push("Journey unavailable: " + j.id);
    return valid;
  });
  const discoveries = catalog.discoveries.filter((d) => {
    const valid =
      nodes.has(d.nodeId) && hintValid(d.presentation) && sourced(d.sourceIds);
    if (!valid) issues.push("Discovery unavailable: " + d.id);
    return valid;
  });
  const discoveryIds = new Set(discoveries.map((d) => d.id));
  const loreThreads = catalog.loreThreads.filter((t) => {
    const valid =
      scoped(t) &&
      nodes.has(t.conceptNodeId) &&
      hintValid(t.presentation) &&
      t.discoveryIds.length > 0 &&
      t.discoveryIds.includes(t.initialDiscoveryId) &&
      t.discoveryIds.every(
        (id) =>
          discoveryIds.has(id) &&
          discoveries.find((d) => d.id === id)?.threadId === t.id,
      );
    if (!valid) issues.push("Lore thread unavailable: " + t.id);
    return valid;
  });
  const threadIds = new Set(loreThreads.map((t) => t.id));
  const resolved: NarrativeCatalog = {
    availability: catalog.availability,
    schemaVersion: 1,
    sources: catalog.sources.filter((s) => sources.has(s.id)),
    journeys,
    loreThreads,
    discoveries: discoveries
      .filter((d) => threadIds.has(d.threadId))
      .map((d) => ({
        ...d,
        relatedDiscoveryIds: d.relatedDiscoveryIds.filter(
          (id) =>
            discoveryIds.has(id) &&
            discoveries.find((other) => other.id === id)?.threadId ===
              d.threadId,
        ),
      })),
  };
  return { catalog: resolved, issues };
}
