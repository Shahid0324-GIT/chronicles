import { createStore } from "zustand/vanilla";
import { createNarrativeState, type NarrativeState } from "./narrative-state";
import type {
  ExplorationMode,
  NarrativeDataProvider,
} from "@/features/narrative/contracts";
import { LocalNarrativeDataProvider } from "@/features/narrative/provider";
import type {
  GraphNode,
  NodeType,
  Universe,
  UniverseGraph,
} from "@/lib/contracts";
import type { AtlasEvent } from "@/features/graph/events";
import { NODE_TYPES } from "@/features/graph/identity";
import { filterGraph } from "@/features/graph/filter";
import { deriveJourney } from "@/features/journey/journey";
export interface CameraPosition {
  x: number;
  y: number;
  ratio: number;
  angle: number;
}
export type CameraCommand =
  | "restore"
  | "focus"
  | "reset"
  | "zoom-in"
  | "zoom-out"
  | "pan-left"
  | "pan-right"
  | "pan-up"
  | "pan-down";
export interface ExplorationState extends NarrativeState {
  refreshAtlas: () => Promise<void>;
  graph: UniverseGraph | null;
  activeUniverse: Universe | null;
  status: "ready" | "loading" | "error";
  error: string | null;
  loadVersion: number;
  selectedId: string | null;
  selectedEdgeId: string | null;
  panelMinimized: boolean;
  mode: ExplorationMode;
  continuityId: string | null;
  types: NodeType[];
  query: string;
  camera: CameraPosition;
  cameraRequest: {
    command: CameraCommand;
    version: number;
    target?: CameraPosition;
  };
  journeyIndex: number;
  discoveredIds: string[];
  researchProgress: { completed: number; total: number } | null;
  beginUniverse: (universe: Universe) => number;
  completeUniverse: (token: number, graph: UniverseGraph) => void;
  failUniverse: (token: number, message: string) => void;
  selectNode: (id: string, source?: "journey" | "inspection") => void;
  selectEdge: (id: string) => void;
  clearSelection: () => void;
  minimizePanel: () => void;
  setContinuity: (id: string | null) => void;
  toggleType: (type: NodeType) => void;
  resetFilters: () => void;
  setQuery: (query: string) => void;
  setMode: (mode: ExplorationMode) => void;
  stepJourney: (delta: number) => void;
  requestCamera: (command: CameraCommand) => void;
  setCamera: (camera: CameraPosition) => void;
  consume: (event: AtlasEvent) => void;
}
export const DEFAULT_CAMERA: CameraPosition = {
  x: 0.5,
  y: 0.5,
  angle: 0,
  ratio: 1.12,
};
export function createExplorationStore(
  initialGraph: UniverseGraph | null = null,
  provider: NarrativeDataProvider = new LocalNarrativeDataProvider(),
) {
  return createStore<ExplorationState>()((set, get) => ({
    ...createNarrativeState(set, get, provider),
    graph: initialGraph,
    activeUniverse: initialGraph?.universe ?? null,
    status: "ready",
    error: null,
    loadVersion: 0,
    selectedId: null,
    selectedEdgeId: null,
    panelMinimized: false,
    mode: "explore",
    continuityId: initialGraph?.continuities[0]?.id ?? null,
    types: [...NODE_TYPES],
    query: "",
    camera: { ...DEFAULT_CAMERA },
    cameraRequest: { command: "reset", version: 0 },
    journeyIndex: 0,
    discoveredIds: [],
    researchProgress: null,
    refreshAtlas: async () => {
      const initial = get();
      if (!initial.activeUniverse) return;
      const response = await fetch(
        `/api/atlas/universes/${encodeURIComponent(initial.activeUniverse.slug)}/graph`,
        { cache: "no-store", signal: AbortSignal.timeout(15000) },
      );
      if (!response.ok) throw new Error("The atlas could not be refreshed.");
      const graph: UniverseGraph = await response.json();
      if (
        get().activeUniverse?.id !== initial.activeUniverse.id ||
        get().continuityId !== initial.continuityId
      )
        return;
      if (
        graph.universe.id !== initial.activeUniverse.id ||
        !Array.isArray(graph.nodes) ||
        !Array.isArray(graph.edges)
      )
        throw new Error("Invalid atlas response.");
      const current = get();
      set({
        graph,
        selectedId: graph.nodes.some((n) => n.id === current.selectedId)
          ? current.selectedId
          : null,
        selectedEdgeId: graph.edges.some((e) => e.id === current.selectedEdgeId)
          ? current.selectedEdgeId
          : null,
      });
    },
    beginUniverse: (universe) => {
      get().resetNarrativeScope();
      const token = get().loadVersion + 1;
      set({
        activeUniverse: universe,
        graph: null,
        selectedEdgeId: null,
        status: "loading",
        error: null,
        loadVersion: token,
        selectedId: null,
        panelMinimized: false,
        mode: "explore",
        continuityId: null,
        types: [...NODE_TYPES],
        query: "",
        camera: { ...DEFAULT_CAMERA },
        journeyIndex: 0,
        discoveredIds: [],
        researchProgress: null,
      });
      return token;
    },
    completeUniverse: (token, graph) => {
      if (
        get().loadVersion === token &&
        get().activeUniverse?.id === graph.universe.id
      )
        set({
          graph,
          status: "ready",
          error: null,
          continuityId: graph.continuities[0]?.id ?? null,
        });
    },
    failUniverse: (token, error) => {
      if (get().loadVersion === token) set({ status: "error", error });
    },
    selectNode: (id, source) => {
      const state = get();
      if (
        state.spoilerPosition !== null &&
        !state.narrative.entryIndex?.some((entry) => entry.id === id)
      )
        return;
      if (!source) {
        const thread = state.narrative.loreThreads.find(
          (t) => t.conceptNodeId === id,
        );
        if (thread) {
          get().enterLore(thread.id);
          return;
        }
      }
      const node = state.graph?.nodes.find((n) => n.id === id);
      if (
        !node ||
        !state.types.includes(node.type) ||
        (state.continuityId &&
          node.continuity_id &&
          node.continuity_id !== state.continuityId)
      )
        return;
      if (source !== "journey") {
        get().bookmarkJourney();
        get().rememberFocus();
      }
      set({
        selectedId: id,
        selectedEdgeId: null,
        mode: source === "journey" ? state.mode : "explore",
        panelMinimized: false,
        query: "",
        cameraRequest: {
          command: "focus",
          version: state.cameraRequest.version + 1,
        },
      });
    },
    selectEdge: (id) => {
      const state = get();
      if (
        state.spoilerPosition !== null &&
        !state.narrative.relations?.some((edge) => edge.id === id)
      )
        return;
      if (!state.graph) return;
      const edge = filterGraph(
        state.graph,
        state.continuityId,
        state.types,
      ).edges.find((e) => e.id === id);
      if (!edge) return;
      get().selectNode(
        state.selectedId === edge.source ? edge.target : edge.source,
      );
      set({ selectedEdgeId: id });
    },
    clearSelection: () => {
      get().bookmarkJourney();
      get().rememberFocus();
      set({
        selectedId: null,
        selectedEdgeId: null,
        panelMinimized: false,
        mode: "explore",
      });
      get().requestCamera("reset");
    },
    minimizePanel: () => set((s) => ({ panelMinimized: !s.panelMinimized })),
    setContinuity: (id) => {
      if (id && !get().graph?.continuities.some((c) => c.id === id)) return;
      get().resetNarrativeScope();
      set({
        mode: "explore",
        continuityId: id,
        selectedId: null,
        selectedEdgeId: null,
        journeyIndex: 0,
        query: "",
      });
      get().requestCamera("reset");
      if (get().mode === "guided") get().setMode("guided");
    },
    toggleType: (type) => {
      get().bookmarkJourney();
      get().rememberFocus();
      set((s) => ({
        types: s.types.includes(type)
          ? s.types.filter((t) => t !== type)
          : [...s.types, type],
        selectedId: null,
        selectedEdgeId: null,
        mode: "explore",
      }));
    },
    resetFilters: () =>
      set({
        types: [...NODE_TYPES],
        selectedId: null,
        selectedEdgeId: null,
        query: "",
      }),
    setQuery: (query) => set({ query }),
    setMode: (mode) => {
      if (mode === "guided" && get().narrative.journeys.length) {
        get().resumeJourney();
        return;
      }
      if (mode === "lore") {
        const thread = get().narrative.loreThreads[0];
        if (thread) get().enterLore(thread.id);
        return;
      }
      if (mode === "explore") {
        get().bookmarkJourney();
        get().rememberFocus();
        set({ mode, layoutKind: "free" });
        return;
      }
      set({ mode, journeyIndex: 0 });
      if (mode === "guided") {
        const s = get();
        if (s.graph) {
          const result = deriveJourney(s.graph, s.continuityId);
          if (result.available) {
            set({ types: [...NODE_TYPES] });
            get().selectNode(result.journey.nodeIds[0], "journey");
          }
        }
      }
    },
    stepJourney: (delta) => {
      if (get().activeJourneyId && get().narrative.journeys.length) {
        get().advanceNarrative(delta);
        return;
      }
      const s = get();
      if (s.mode !== "guided" || !s.graph) return;
      const result = deriveJourney(s.graph, s.continuityId);
      if (!result.available) return;
      const journeyIndex = Math.max(
        0,
        Math.min(result.journey.nodeIds.length - 1, s.journeyIndex + delta),
      );
      set({ journeyIndex });
      get().selectNode(result.journey.nodeIds[journeyIndex], "journey");
    },
    requestCamera: (command) =>
      set((s) => ({
        cameraRequest: { command, version: s.cameraRequest.version + 1 },
      })),
    setCamera: (camera) => set({ camera }),
    consume: (event) => {
      const s = get();
      if (!s.graph || event.universeId !== s.graph.universe.id) return;
      let nodes = s.graph.nodes;
      let edges = s.graph.edges;
      switch (event.type) {
        case "node.added":
        case "node.updated": {
          if (event.node.universe_id !== event.universeId) return;
          if (
            event.node.continuity_id &&
            !s.graph.continuities.some((c) => c.id === event.node.continuity_id)
          )
            return;
          const exists = nodes.some((n) => n.id === event.node.id);
          if (
            (event.type === "node.added" && exists) ||
            (event.type === "node.updated" && !exists)
          )
            return;
          nodes = exists
            ? nodes.map((n) => (n.id === event.node.id ? event.node : n))
            : [...nodes, event.node];
          break;
        }
        case "relationship.added": {
          const source = nodes.find((n) => n.id === event.edge.source),
            target = nodes.find((n) => n.id === event.edge.target);
          if (
            !source ||
            !target ||
            event.edge.universe_id !== event.universeId ||
            edges.some((e) => e.id === event.edge.id) ||
            [source.continuity_id, target.continuity_id].some(
              (id) => id !== null && id !== event.edge.continuity_id,
            )
          )
            return;
          edges = [...edges, event.edge];
          break;
        }
        case "verification.changed":
          nodes = nodes.map((n) =>
            n.id === event.nodeId
              ? {
                  ...n,
                  metadata: {
                    ...n.metadata,
                    verification_status: event.status,
                  },
                }
              : n,
          );
          break;
        case "discovery.revealed":
          if (nodes.some((n) => n.id === event.nodeId))
            set({
              discoveredIds: [...new Set([...s.discoveredIds, event.nodeId])],
            });
          return;
        case "research.progress":
          if (
            Number.isInteger(event.total) &&
            Number.isInteger(event.completed) &&
            event.total > 0 &&
            event.completed >= 0 &&
            event.completed <= event.total
          )
            set({
              researchProgress: {
                completed: event.completed,
                total: event.total,
              },
            });
          return;
      }
      const selected: GraphNode | undefined = nodes.find(
        (n) => n.id === s.selectedId,
      );
      set({
        graph: { ...s.graph, nodes, edges },
        selectedEdgeId: null,
        selectedId:
          selected &&
          s.types.includes(selected.type) &&
          (!s.continuityId ||
            !selected.continuity_id ||
            selected.continuity_id === s.continuityId)
            ? selected.id
            : null,
      });
    },
  }));
}
export type ExplorationStore = ReturnType<typeof createExplorationStore>;
