import type { UniverseGraph } from "@/lib/contracts";
import type { NarrativeCatalog } from "./contracts";

/** A bounded reader never traverses raw canonical edges or names from a later source. */
export function readerGraph(
  graph: UniverseGraph,
  catalog: NarrativeCatalog,
  boundary: number | null,
): UniverseGraph {
  if (boundary === null) return graph;
  const entries = new Map(
    catalog.entryIndex?.map((entry) => [entry.id, entry]) ?? [],
  );
  const acceptedEdges = new Set(
    catalog.relations?.map((edge) => edge.id) ?? [],
  );
  const nodes = graph.nodes
    .filter((node) => entries.has(node.id))
    .map((node) => ({
      ...node,
      title: entries.get(node.id)!.displayTitle,
      summary: "",
    }));
  const ids = new Set(nodes.map((node) => node.id));
  return {
    ...graph,
    nodes,
    edges: graph.edges.filter(
      (edge) =>
        acceptedEdges.has(edge.id) &&
        ids.has(edge.source) &&
        ids.has(edge.target),
    ),
  };
}
