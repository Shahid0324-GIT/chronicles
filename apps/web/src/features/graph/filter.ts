import type { NodeType, UniverseGraph } from "@/lib/contracts";
export function filterGraph(
  graph: UniverseGraph,
  continuity: string | null,
  types: NodeType[],
): UniverseGraph {
  const nodes = graph.nodes.filter(
    (n) =>
      (!continuity || !n.continuity_id || n.continuity_id === continuity) &&
      types.includes(n.type),
  );
  const ids = new Set(nodes.map((n) => n.id));
  return {
    ...graph,
    nodes,
    edges: graph.edges.filter(
      (e) =>
        ids.has(e.source) &&
        ids.has(e.target) &&
        (!continuity || !e.continuity_id || e.continuity_id === continuity),
    ),
  };
}
