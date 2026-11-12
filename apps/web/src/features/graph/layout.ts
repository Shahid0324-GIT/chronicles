import type { GraphNode, GraphEdge } from "@/lib/contracts";
import { NODE_IDENTITIES, NODE_TYPES } from "./identity";
export interface Point {
  x: number;
  y: number;
}
// Semantic clusters, deterministic degree ordering, then ID tie-breaks. No randomness or chronology.
export function layoutNodes(
  nodes: GraphNode[],
  edges: GraphEdge[],
  previous = new Map<string, Point>(),
): Map<string, Point> {
  const positions = new Map<string, Point>();
  const degree = new Map<string, number>();
  for (const edge of edges)
    for (const id of [edge.source, edge.target])
      degree.set(id, (degree.get(id) ?? 0) + 1);
  for (const type of NODE_TYPES) {
    const group = nodes
      .filter((n) => n.type === type)
      .sort(
        (a, b) =>
          (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0) ||
          a.id.localeCompare(b.id),
      );
    const [cx, cy] = NODE_IDENTITIES[type].center;
    group.forEach((node, index) => {
      const angle =
        (index / Math.max(group.length, 1)) * Math.PI * 2 + Math.PI / 6;
      const ring = Math.floor(index / 10);
      const radius =
        group.length === 1
          ? 0
          : (type === "CHARACTER" ? 235 : 115) + ring * 110;
      positions.set(
        node.id,
        previous.get(node.id) ?? {
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius * 0.82,
        },
      );
    });
  }
  return positions;
}
