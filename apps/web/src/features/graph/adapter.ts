import type {
  NarrativeJourney,
  LoreThread,
} from "@/features/narrative/contracts";
import { MultiDirectedGraph } from "graphology";
import type { GraphNode, GraphEdge, UniverseGraph } from "@/lib/contracts";
import { resolveMedia } from "@/features/discovery/media-registry";
import { NODE_IDENTITIES, humanize } from "./identity";
import { layoutNodes, type Point } from "./layout";
export interface AtlasNodeAttributes {
  x: number;
  y: number;
  size: number;
  color: string;
  label: string;
  shape: string;
  image: string;
  aspectRatio: number;
  entity: GraphNode;
  presentationRole: "moment" | "concept" | "supporting";
}
export interface AtlasEdgeAttributes {
  size: number;
  color: string;
  label: string;
  entity: GraphEdge;
  narrativePath: boolean;
  loreLink: boolean;
}
export type AtlasGraph = MultiDirectedGraph<
  AtlasNodeAttributes,
  AtlasEdgeAttributes
>;
export function adaptGraph(
  data: UniverseGraph,
  previous?: Map<string, Point>,
  presentation?: {
    positions: Map<string, Point>;
    journey?: NarrativeJourney;
    thread?: LoreThread;
  },
) {
  const graph: AtlasGraph = new MultiDirectedGraph();
  const issues: string[] = [];
  const positions =
    presentation?.positions ?? layoutNodes(data.nodes, data.edges, previous);
  const moments = new Set(
    presentation?.journey?.steps.map((step) => step.eventNodeId) ?? [],
  );
  const loreEdges = new Set(
    presentation?.thread?.presentation.relationshipIds ?? [],
  );
  for (const node of data.nodes) {
    if (
      graph.hasNode(node.id) ||
      node.universe_id !== data.universe.id ||
      !NODE_IDENTITIES[node.type]
    ) {
      issues.push(`Invalid node ${node.id}`);
      continue;
    }
    const visual = NODE_IDENTITIES[node.type];
    graph.addNode(node.id, {
      ...positions.get(node.id)!,
      size: moments.has(node.id)
        ? 34
        : node.id === presentation?.thread?.conceptNodeId
          ? 38
          : node.type === "CHARACTER"
            ? 29
            : node.type === "LOCATION"
              ? 29
              : 23,
      presentationRole: moments.has(node.id)
        ? "moment"
        : node.id === presentation?.thread?.conceptNodeId
          ? "concept"
          : "supporting",
      color: visual.color,
      label:
        node.title.length > 24 ? node.title.slice(0, 22) + "…" : node.title,
      shape: visual.shape,
      aspectRatio:
        node.type === "CHARACTER" ? 0.82 : node.type === "LOCATION" ? 1.5 : 1,
      image: resolveMedia(node.id, node.type).src,
      entity: node,
    });
  }
  for (const edge of data.edges) {
    if (
      graph.hasEdge(edge.id) ||
      !graph.hasNode(edge.source) ||
      !graph.hasNode(edge.target) ||
      edge.universe_id !== data.universe.id
    ) {
      issues.push(`Invalid edge ${edge.id}`);
      continue;
    }
    const scoped = [
      graph.getNodeAttribute(edge.source, "entity").continuity_id,
      graph.getNodeAttribute(edge.target, "entity").continuity_id,
    ].filter((id): id is string => id !== null);
    if (scoped.some((id) => id !== edge.continuity_id)) {
      issues.push(`Incompatible edge ${edge.id}`);
      continue;
    }
    graph.addDirectedEdgeWithKey(edge.id, edge.source, edge.target, {
      size: edge.relationship_type === "ALLIED_WITH" ? 1.2 : 0.8,
      color:
        edge.relationship_type === "ALLIED_WITH"
          ? "#8cafa1"
          : edge.relationship_type === "PARTICIPATED_IN"
            ? "#c99773"
            : "#718082",
      label: humanize(edge.relationship_type),
      entity: edge,
      narrativePath: Boolean(
        presentation?.journey?.steps.some(
          (step, index, steps) =>
            index > 0 &&
            ((steps[index - 1].eventNodeId === edge.source &&
              step.eventNodeId === edge.target) ||
              (steps[index - 1].eventNodeId === edge.target &&
                step.eventNodeId === edge.source)),
        ),
      ),
      loreLink: loreEdges.has(edge.id),
    });
  }
  return { graph, positions, issues };
}
