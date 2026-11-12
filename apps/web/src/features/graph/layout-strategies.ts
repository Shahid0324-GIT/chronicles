import type { UniverseGraph } from "@/lib/contracts";
import type {
  LayoutKind,
  NarrativeJourney,
  LoreThread,
  Discovery,
} from "@/features/narrative/contracts";
import { layoutNodes, type Point } from "./layout";
export interface LayoutContext {
  graph: UniverseGraph;
  journey?: NarrativeJourney;
  thread?: LoreThread;
  discoveries: Discovery[];
  previous: Map<string, Point>;
}
export interface GraphLayoutStrategy {
  readonly kind: LayoutKind;
  compute(context: LayoutContext): Map<string, Point>;
}
export class FreeExplorationLayout implements GraphLayoutStrategy {
  readonly kind = "free";
  compute({ graph, previous }: LayoutContext) {
    return layoutNodes(graph.nodes, graph.edges, previous);
  }
}
function attachRemaining(
  context: LayoutContext,
  positions: Map<string, Point>,
  anchors: { point: Point; relatedIds: string[] }[],
) {
  const remaining = context.graph.nodes
    .filter((n) => !positions.has(n.id))
    .sort((a, b) => a.id.localeCompare(b.id));
  const groups = new Map<number, string[]>();
  for (const node of remaining) {
    const neighbors = new Set(
      context.graph.edges
        .filter((e) => e.source === node.id || e.target === node.id)
        .flatMap((e) => [e.source, e.target]),
    );
    const index = anchors.findIndex(
      (a) =>
        a.relatedIds.includes(node.id) ||
        a.relatedIds.some((id) => neighbors.has(id)),
    );
    const key = index < 0 ? anchors.length : index;
    groups.set(key, [...(groups.get(key) ?? []), node.id]);
  }
  for (const [index, ids] of groups)
    ids.forEach((id, slot) => {
      const anchor = anchors[index]?.point ?? { x: 0, y: -330 };
      positions.set(
        id,
        context.previous.get(id) ?? {
          x: anchor.x + ((slot % 3) - 1) * 135,
          y:
            anchor.y + (slot % 2 ? -1 : 1) * (195 + Math.floor(slot / 3) * 125),
        },
      );
    });
  return positions;
}
export class NarrativeLayout implements GraphLayoutStrategy {
  readonly kind = "narrative";
  compute(context: LayoutContext) {
    if (!context.journey) return new FreeExplorationLayout().compute(context);
    const positions = new Map<string, Point>(),
      steps = context.journey.steps;
    const anchors = steps.map((step, index) => {
      const point = context.previous.get(step.eventNodeId) ?? {
        x: (index - (steps.length - 1) / 2) * 340,
        y: [25, -80, 70, -20][index % 4],
      };
      positions.set(step.eventNodeId, point);
      return {
        point,
        relatedIds: [step.eventNodeId, ...step.presentation.relatedNodeIds],
      };
    });
    return attachRemaining(context, positions, anchors);
  }
}
export class LoreRelationshipLayout implements GraphLayoutStrategy {
  readonly kind = "lore";
  compute(context: LayoutContext) {
    if (!context.thread) return new FreeExplorationLayout().compute(context);
    const positions = new Map<string, Point>([
      [context.thread.conceptNodeId, { x: 0, y: 0 }],
    ]);
    const centers = {
      established: { x: -290, y: 140 },
      interpretation: { x: -100, y: -265 },
      unresolved: { x: 340, y: -140 },
    };
    const counts = { established: 0, interpretation: 0, unresolved: 0 };
    const discoveries = context.thread.discoveryIds
      .map((id) => context.discoveries.find((d) => d.id === id))
      .filter((d): d is Discovery => Boolean(d));
    const anchors = [
      { point: { x: 0, y: 0 }, relatedIds: [context.thread.conceptNodeId] },
    ];
    for (const discovery of discoveries) {
      const center = centers[discovery.classification],
        index = counts[discovery.classification]++;
      const point = context.previous.get(discovery.nodeId) ?? {
        x: center.x + index * 370,
        y: center.y + index * 65,
      };
      if (!positions.has(discovery.nodeId))
        positions.set(discovery.nodeId, point);
      anchors.push({
        point,
        relatedIds: [
          discovery.nodeId,
          ...discovery.presentation.relatedNodeIds,
        ],
      });
    }
    return attachRemaining(context, positions, anchors);
  }
}
const strategies: Record<LayoutKind, GraphLayoutStrategy> = {
  narrative: new NarrativeLayout(),
  lore: new LoreRelationshipLayout(),
  free: new FreeExplorationLayout(),
};
export const layoutStrategy = (kind: LayoutKind) => strategies[kind];
