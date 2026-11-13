"use client";
import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useStore } from "zustand";
import type { NarrativeDataProvider } from "@/features/narrative/contracts";
import { BackendNarrativeDataProvider } from "@/features/narrative/provider";
import type { UniverseGraph } from "@/lib/contracts";
import { createExplorationStore, type ExplorationStore } from "./exploration";
const Context = createContext<ExplorationStore | null>(null);
export function ExplorationProvider({
  graph,
  children,
  provider,
}: {
  graph: UniverseGraph | null;
  children: ReactNode;
  provider?: NarrativeDataProvider;
}) {
  const [store] = useState(() =>
    createExplorationStore(
      graph,
      provider ?? new BackendNarrativeDataProvider(),
    ),
  );
  return (
    <Context.Provider value={store}>
      <NarrativeLoader store={store} />
      {children}
    </Context.Provider>
  );
}
export function useExploration<T>(
  selector: (state: ReturnType<ExplorationStore["getState"]>) => T,
): T {
  const store = useContext(Context);
  if (!store)
    throw new Error("Exploration state requires an ExplorationProvider");
  return useStore(store, selector);
}
export function useExplorationApi() {
  const store = useContext(Context);
  if (!store)
    throw new Error("Exploration state requires an ExplorationProvider");
  return store;
}

function NarrativeLoader({ store }: { store: ExplorationStore }) {
  const graph = useStore(store, (state) => state.graph),
    continuity = useStore(store, (state) => state.continuityId);
  useEffect(() => {
    if (!graph) return;
    const controller = new AbortController();
    void store.getState().loadNarrative(controller.signal);
    return () => controller.abort();
  }, [graph, continuity, store]);
  return null;
}
