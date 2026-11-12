import type { GraphNode, GraphEdge } from "@/lib/contracts";
// Transport-independent consumer seam. No SSE connection or simulated producer is implemented.
export type AtlasEvent = { universeId: string } & (
  | { type: "node.added"; node: GraphNode }
  | { type: "node.updated"; node: GraphNode }
  | { type: "relationship.added"; edge: GraphEdge }
  | {
      type: "verification.changed";
      nodeId: string;
      status: "unverified" | "verified" | "disputed";
    }
  | { type: "discovery.revealed"; nodeId: string }
  | { type: "research.progress"; completed: number; total: number }
);
export interface AtlasEventConsumer {
  consume: (event: AtlasEvent) => void;
}
