"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import { useStore } from "zustand";
import type { UniverseGraph } from "@/lib/contracts";
import { createExplorationStore, type ExplorationStore } from "./exploration";
const Context = createContext<ExplorationStore | null>(null);
export function ExplorationProvider({
  graph,
  children,
}: {
  graph: UniverseGraph | null;
  children: ReactNode;
}) {
  const [store] = useState(() => createExplorationStore(graph));
  return <Context.Provider value={store}>{children}</Context.Provider>;
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
