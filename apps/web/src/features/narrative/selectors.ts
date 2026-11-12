import type { UniverseGraph } from "@/lib/contracts";
import type {
  NarrativeCatalog,
  ExplorationMode,
  PresentationHint,
} from "./contracts";
export interface NarrativeSelection {
  narrative: NarrativeCatalog;
  activeJourneyId: string | null;
  journeyIndex: number;
  activeLoreThreadId: string | null;
  currentDiscoveryId: string | null;
  mode: ExplorationMode;
}
export const activeJourney = (state: NarrativeSelection) =>
  state.narrative.journeys.find((j) => j.id === state.activeJourneyId);
export const activeStep = (state: NarrativeSelection) =>
  activeJourney(state)?.steps[state.journeyIndex];
export const activeThread = (state: NarrativeSelection) =>
  state.narrative.loreThreads.find((t) => t.id === state.activeLoreThreadId);
export const activeDiscovery = (state: NarrativeSelection) =>
  state.narrative.discoveries.find(
    (d) =>
      d.id === state.currentDiscoveryId &&
      d.threadId === state.activeLoreThreadId,
  );
export function activePresentation(
  state: NarrativeSelection,
): PresentationHint | undefined {
  return state.mode === "guided"
    ? activeStep(state)?.presentation
    : state.mode === "lore"
      ? activeDiscovery(state)?.presentation
      : undefined;
}
export function narrativeHighlights(
  state: NarrativeSelection,
  graph: UniverseGraph,
) {
  const hint = activePresentation(state);
  const nodeIds = new Set(hint?.relatedNodeIds ?? []),
    edgeIds = new Set(hint?.relationshipIds ?? []);
  const focus =
    state.mode === "guided"
      ? activeStep(state)?.eventNodeId
      : state.mode === "lore"
        ? activeDiscovery(state)?.nodeId
        : undefined;
  if (focus) nodeIds.add(focus);
  for (const edge of graph.edges)
    if (edgeIds.has(edge.id)) {
      nodeIds.add(edge.source);
      nodeIds.add(edge.target);
    }
  return { nodeIds, edgeIds, focus };
}
