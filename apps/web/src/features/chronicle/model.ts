import type { GraphEdge, GraphNode, UniverseGraph } from "@/lib/contracts";
import type {
  NarrativeCatalog,
  NarrativeJourney,
  JourneyStep,
} from "@/features/narrative/contracts";
import { CHRONICLE_DESIGN } from "./design";
export type BranchKind =
  "characters" | "lore" | "locations" | "mysteries" | "objects";
export const BRANCHES: { kind: BranchKind; label: string; glyph: string }[] = [
  { kind: "characters", label: "Characters", glyph: "♧" },
  { kind: "lore", label: "Lore", glyph: "◎" },
  { kind: "locations", label: "Places", glyph: "⌂" },
  { kind: "mysteries", label: "Mysteries", glyph: "?" },
  { kind: "objects", label: "Objects", glyph: "◇" },
];
export interface EventConnection {
  node: GraphNode;
  edge: GraphEdge;
}
export function eventRegion(
  graph: UniverseGraph,
  step: JourneyStep,
  catalog: NarrativeCatalog,
  continuityId: string | null,
) {
  const nodes = new Map(
    graph.nodes
      .filter(
        (n) =>
          n.universe_id === graph.universe.id &&
          (!n.continuity_id || n.continuity_id === continuityId),
      )
      .map((n) => [n.id, n]),
  );
  const edges = graph.edges.filter(
    (e) =>
      e.universe_id === graph.universe.id &&
      (!e.continuity_id || e.continuity_id === continuityId) &&
      nodes.has(e.source) &&
      nodes.has(e.target),
  );
  const direct = edges.filter(
    (e) =>
      (e.source === step.eventNodeId || e.target === step.eventNodeId) &&
      (catalog.availability?.kind !== "generated" ||
        step.presentation.relationshipIds.includes(e.id)),
  );
  const ids = new Set([
    ...step.presentation.relatedNodeIds,
    ...direct.flatMap((e) => [e.source, e.target]),
  ]);
  ids.delete(step.eventNodeId);
  const related = [...ids]
    .map((id) => nodes.get(id))
    .filter((n): n is GraphNode => Boolean(n))
    .map((node) =>
      catalog.availability?.kind === "generated"
        ? {
            ...node,
            title:
              catalog.entryIndex?.find((entry) => entry.id === node.id)
                ?.displayTitle ?? "Related entry",
          }
        : node,
    )
    .sort((a, b) => a.title.localeCompare(b.title));
  const connections = (incoming: boolean): EventConnection[] =>
    direct
      .filter(
        (e) =>
          (e.relationship_type === "CAUSED" ||
            e.relationship_type === "ENABLED") &&
          (incoming
            ? e.target === step.eventNodeId
            : e.source === step.eventNodeId),
      )
      .flatMap((edge) => {
        const node = nodes.get(incoming ? edge.source : edge.target);
        return node
          ? [
              {
                node:
                  catalog.availability?.kind === "generated"
                    ? {
                        ...node,
                        title:
                          catalog.entryIndex?.find(
                            (entry) => entry.id === node.id,
                          )?.displayTitle ?? "Related entry",
                      }
                    : node,
                edge,
              },
            ]
          : [];
      });
  return {
    causes: connections(true),
    consequences: connections(false),
    characters: related.filter((n) => n.type === "CHARACTER"),
    locations: related.filter((n) => n.type === "LOCATION"),
    mysteries: related.filter((n) => n.type === "MYSTERY"),
    objects: related.filter((n) => n.type === "OBJECT"),
    lore: catalog.loreThreads.filter(
      (t) =>
        t.universeId === graph.universe.id &&
        t.continuityId === continuityId &&
        (step.loreThreadIds.includes(t.id) || ids.has(t.conceptNodeId)),
    ),
  };
}
/** Only a window is represented; the complete provider journey retains all steps. */
export function spineLayout(journey: NarrativeJourney, index: number) {
  const { maxVisible, start, end } = CHRONICLE_DESIGN.spine;
  const count = Math.min(journey.steps.length, maxVisible);
  const first = Math.max(
    0,
    Math.min(journey.steps.length - count, index - Math.floor(count / 2)),
  );
  return journey.steps.slice(first, first + count).map((step, slot) => ({
    step,
    index: first + slot,
    x: count === 1 ? 50 : start + ((end - start) * slot) / (count - 1),
    position:
      first + slot < index
        ? "earlier"
        : first + slot === index
          ? "current"
          : "upcoming",
  }));
}
