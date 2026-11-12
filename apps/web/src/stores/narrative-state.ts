import type { StoreApi } from "zustand/vanilla";
import type { NodeType } from "@/lib/contracts";
import type {
  ExplorationMode,
  LayoutKind,
  NarrativeCatalog,
  NarrativeDataProvider,
} from "@/features/narrative/contracts";
import { emptyNarrativeCatalog } from "@/features/narrative/contracts";
import { resolveNarrative } from "@/features/narrative/resolve";
import {
  activeJourney,
  activeStep,
  activeThread,
} from "@/features/narrative/selectors";
import { NODE_TYPES } from "@/features/graph/identity";
import type { CameraPosition, ExplorationState } from "./exploration";

export interface FocusFrame {
  universeId: string;
  continuityId: string | null;
  mode: ExplorationMode;
  layout: LayoutKind;
  selectedId: string | null;
  selectedEdgeId: string | null;
  journeyId: string | null;
  journeyIndex: number;
  threadId: string | null;
  discoveryId: string | null;
  camera: CameraPosition;
  types: NodeType[];
}
export interface NarrativeState {
  narrative: NarrativeCatalog;
  narrativeStatus: "idle" | "loading" | "ready" | "error";
  narrativeError: string | null;
  narrativeIssues: string[];
  narrativeRequest: number;
  activeJourneyId: string | null;
  activeLoreThreadId: string | null;
  currentDiscoveryId: string | null;
  layoutKind: LayoutKind;
  journeyProgress: Record<string, number>;
  journeyBookmark: FocusFrame | null;
  focusHistory: FocusFrame[];
  loadNarrative: (signal?: AbortSignal) => Promise<void>;
  resetNarrativeScope: () => void;
  rememberFocus: () => void;
  bookmarkJourney: () => void;
  beginJourney: (id: string, restart?: boolean) => void;
  advanceNarrative: (delta: number) => void;
  enterLore: (threadId: string, discoveryId?: string) => void;
  selectDiscovery: (id: string) => void;
  resumeJourney: () => void;
  backFocus: () => void;
  setLayout: (kind: LayoutKind) => void;
}
function snapshot(state: ExplorationState): FocusFrame | null {
  if (!state.activeUniverse) return null;
  return {
    universeId: state.activeUniverse.id,
    continuityId: state.continuityId,
    mode: state.mode,
    layout: state.layoutKind,
    selectedId: state.selectedId,
    selectedEdgeId: state.selectedEdgeId,
    journeyId: state.activeJourneyId,
    journeyIndex: state.journeyIndex,
    threadId: state.activeLoreThreadId,
    discoveryId: state.currentDiscoveryId,
    camera: { ...state.camera },
    types: [...state.types],
  };
}
const progressKey = (state: ExplorationState, id: string) =>
  [state.activeUniverse?.id, state.continuityId, id].join(":");
export function createNarrativeState(
  set: StoreApi<ExplorationState>["setState"],
  get: () => ExplorationState,
  provider: NarrativeDataProvider,
): NarrativeState {
  const focus = (selectedId: string, mode: ExplorationMode) => {
    const s = get();
    set({
      mode,
      selectedId,
      selectedEdgeId: null,
      panelMinimized: false,
      query: "",
      types: [...NODE_TYPES],
      cameraRequest: { command: "focus", version: s.cameraRequest.version + 1 },
    });
  };
  return {
    narrative: emptyNarrativeCatalog(),
    narrativeStatus: "idle",
    narrativeError: null,
    narrativeIssues: [],
    narrativeRequest: 0,
    activeJourneyId: null,
    activeLoreThreadId: null,
    currentDiscoveryId: null,
    layoutKind: "free",
    journeyProgress: {},
    journeyBookmark: null,
    focusHistory: [],
    loadNarrative: async (signal) => {
      const initial = get(),
        graph = initial.graph;
      if (!graph) return;
      const request = initial.narrativeRequest + 1,
        continuity = initial.continuityId;
      set({
        narrativeRequest: request,
        narrativeStatus: "loading",
        narrativeError: null,
      });
      try {
        const response = await provider.load(
          { universeId: graph.universe.id, continuityId: continuity },
          signal,
        );
        const current = get();
        if (
          signal?.aborted ||
          current.narrativeRequest !== request ||
          current.graph?.universe.id !== graph.universe.id ||
          current.continuityId !== continuity
        )
          return;
        const result = resolveNarrative(response, graph, continuity);
        const journey =
          result.catalog.journeys.find(
            (j) => j.id === current.activeJourneyId,
          ) ?? result.catalog.journeys[0];
        set({
          narrative: result.catalog,
          narrativeIssues: result.issues,
          narrativeStatus: "ready",
          activeJourneyId: journey?.id ?? null,
          layoutKind:
            journey && current.layoutKind === "free" && !current.selectedId
              ? "narrative"
              : current.layoutKind,
        });
        // Start the editorial introduction only when a fresh atlas has not been interacted with.
        if (
          journey &&
          !current.selectedId &&
          !current.query &&
          current.focusHistory.length === 0
        )
          get().beginJourney(journey.id);
        else if (!journey && current.mode === "guided")
          set({ mode: "explore", layoutKind: "free" });
      } catch (error) {
        if (signal?.aborted || get().narrativeRequest !== request) return;
        set({
          narrative: emptyNarrativeCatalog(),
          narrativeStatus: "error",
          narrativeError:
            error instanceof Error
              ? error.message
              : "Narrative notes are unavailable.",
        });
      }
    },
    resetNarrativeScope: () =>
      set((s) => ({
        narrative: emptyNarrativeCatalog(),
        narrativeStatus: "idle",
        narrativeError: null,
        narrativeIssues: [],
        narrativeRequest: s.narrativeRequest + 1,
        activeJourneyId: null,
        activeLoreThreadId: null,
        currentDiscoveryId: null,
        layoutKind: "free",
        journeyBookmark: null,
        focusHistory: [],
      })),
    rememberFocus: () => {
      const s = get(),
        frame = snapshot(s);
      if (frame) set({ focusHistory: [...s.focusHistory, frame].slice(-40) });
    },
    bookmarkJourney: () => {
      const s = get();
      if (s.mode === "guided" && activeJourney(s))
        set({ journeyBookmark: snapshot(s) });
    },
    beginJourney: (id, restart = false) => {
      const s = get(),
        journey = s.narrative.journeys.find((j) => j.id === id);
      if (!journey || !s.graph || journey.continuityId !== s.continuityId)
        return;
      const key = progressKey(s, id);
      const index = restart
        ? 0
        : Math.min(journey.steps.length - 1, s.journeyProgress[key] ?? 0);
      get().rememberFocus();
      set({
        activeJourneyId: id,
        journeyIndex: index,
        layoutKind: "narrative",
        journeyBookmark: null,
        journeyProgress: { ...s.journeyProgress, [key]: index },
      });
      focus(journey.steps[index].eventNodeId, "guided");
    },
    advanceNarrative: (delta) => {
      const s = get(),
        journey = activeJourney(s);
      if (s.mode !== "guided" || !journey || !Number.isInteger(delta)) return;
      const index = Math.max(
        0,
        Math.min(journey.steps.length - 1, s.journeyIndex + delta),
      );
      if (index === s.journeyIndex) return;
      get().rememberFocus();
      set({
        journeyIndex: index,
        journeyProgress: {
          ...s.journeyProgress,
          [progressKey(s, journey.id)]: index,
        },
      });
      focus(journey.steps[index].eventNodeId, "guided");
    },
    enterLore: (threadId, discoveryId) => {
      const s = get(),
        thread = s.narrative.loreThreads.find((t) => t.id === threadId);
      if (!thread || thread.continuityId !== s.continuityId) return;
      const id = discoveryId ?? thread.initialDiscoveryId;
      const discovery = s.narrative.discoveries.find(
        (d) => d.id === id && d.threadId === threadId,
      );
      if (!discovery || !thread.discoveryIds.includes(id)) return;
      get().bookmarkJourney();
      get().rememberFocus();
      set({
        activeLoreThreadId: thread.id,
        currentDiscoveryId: discovery.id,
        layoutKind: "lore",
      });
      focus(discovery.nodeId, "lore");
    },
    selectDiscovery: (id) => {
      const s = get(),
        thread = activeThread(s),
        discovery = s.narrative.discoveries.find(
          (d) => d.id === id && d.threadId === thread?.id,
        );
      if (!thread || !discovery || !thread.discoveryIds.includes(id)) return;
      get().rememberFocus();
      set({ currentDiscoveryId: id, layoutKind: "lore" });
      focus(discovery.nodeId, "lore");
    },
    resumeJourney: () => {
      const id = get().journeyBookmark?.journeyId ?? get().activeJourneyId;
      if (id) get().beginJourney(id);
    },
    backFocus: () => {
      const s = get(),
        history = [...s.focusHistory];
      let frame = history.pop();
      while (
        frame &&
        (frame.universeId !== s.activeUniverse?.id ||
          frame.continuityId !== s.continuityId ||
          (frame.selectedId &&
            !s.graph?.nodes.some((n) => n.id === frame!.selectedId)))
      )
        frame = history.pop();
      if (!frame) return;
      set({
        focusHistory: history,
        mode: frame.mode,
        layoutKind: frame.layout,
        selectedId: frame.selectedId,
        selectedEdgeId: frame.selectedEdgeId,
        activeJourneyId: frame.journeyId,
        journeyIndex: frame.journeyIndex,
        activeLoreThreadId: frame.threadId,
        currentDiscoveryId: frame.discoveryId,
        types: frame.types,
        panelMinimized: false,
        query: "",
        cameraRequest: {
          command: "restore",
          version: s.cameraRequest.version + 1,
          target: frame.camera,
        },
      });
      const restored = get(),
        journey = activeJourney(restored);
      if (journey)
        set({
          journeyProgress: {
            ...restored.journeyProgress,
            [progressKey(restored, journey.id)]: frame.journeyIndex,
          },
        });
    },
    setLayout: (kind) => {
      const s = get();
      if (kind === "narrative" && !activeJourney(s)) return;
      if (kind === "lore" && !activeThread(s)) return;
      get().rememberFocus();
      set({ layoutKind: kind });
      get().requestCamera("reset");
    },
  };
}

/** Keep direct graph inspection separate from the curated narrative's meaning. */
export function currentNarrativeNode(state: ExplorationState) {
  return state.mode === "guided"
    ? activeStep(state)?.eventNodeId
    : state.mode === "lore"
      ? state.narrative.discoveries.find(
          (d) => d.id === state.currentDiscoveryId,
        )?.nodeId
      : undefined;
}
