import type { UniverseGraph } from "@/lib/contracts";
export interface Journey {
  id: string;
  title: string;
  source: string;
  continuityId: string;
  nodeIds: string[];
}
export type JourneyResult =
  { available: true; journey: Journey } | { available: false; reason: string };
// Optional metadata convention, not an inferred timeline. The seed deliberately has no such data.
export function deriveJourney(
  graph: UniverseGraph,
  continuity: string | null,
): JourneyResult {
  const unavailable = {
    available: false as const,
    reason:
      "This atlas has connections, but no sourced story order yet. Explore freely while its chronology is uncharted.",
  };
  if (!continuity)
    return {
      available: false,
      reason:
        "Choose one continuity to look for an ordered journey. Adaptations do not share an assumed timeline.",
    };
  const groups = new Map<
    string,
    { nodeId: string; order: number; title: string; source: string }[]
  >();
  for (const node of graph.nodes) {
    if (node.type !== "EVENT" || node.continuity_id !== continuity) continue;
    const value = node.metadata.journey;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    const item = value as Record<string, unknown>;
    if (
      typeof item.id !== "string" ||
      !item.id ||
      typeof item.title !== "string" ||
      typeof item.source !== "string" ||
      !/^https?:\/\//.test(item.source) ||
      typeof item.order !== "number" ||
      !Number.isInteger(item.order) ||
      item.order < 0 ||
      item.order_verified !== true
    )
      continue;
    const entries = groups.get(item.id) ?? [];
    entries.push({
      nodeId: node.id,
      order: item.order,
      title: item.title,
      source: item.source,
    });
    groups.set(item.id, entries);
  }
  for (const [id, entries] of [...groups].sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    entries.sort((a, b) => a.order - b.order);
    if (
      entries.length < 2 ||
      new Set(entries.map((e) => e.order)).size !== entries.length ||
      entries.some(
        (e) => e.source !== entries[0].source || e.title !== entries[0].title,
      )
    )
      continue;
    // Ordering alone does not establish connectivity. Every consecutive pair must be linked.
    const connected = entries
      .slice(1)
      .every((entry, index) =>
        graph.edges.some(
          (e) =>
            e.continuity_id === continuity &&
            ((e.source === entries[index].nodeId &&
              e.target === entry.nodeId) ||
              (e.target === entries[index].nodeId &&
                e.source === entry.nodeId)),
        ),
      );
    if (connected)
      return {
        available: true,
        journey: {
          id,
          title: entries[0].title,
          source: entries[0].source,
          continuityId: continuity,
          nodeIds: entries.map((e) => e.nodeId),
        },
      };
  }
  return unavailable;
}
