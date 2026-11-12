"use client";
import { useCallback, useEffect, useRef } from "react";
import type { Universe, UniverseGraph } from "@/lib/contracts";
import { useExplorationApi } from "@/stores/ExplorationProvider";
export function useUniverseLoader() {
  const store = useExplorationApi();
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  return useCallback(
    async (universe: Universe) => {
      pending.current?.abort();
      const controller = new AbortController();
      pending.current = controller;
      const token = store.getState().beginUniverse(universe);
      try {
        const response = await fetch(
          `/api/atlas/universes/${encodeURIComponent(universe.slug)}/graph`,
          { signal: controller.signal, cache: "no-store" },
        );
        if (!response.ok)
          throw new Error(
            "The local atlas could not be opened. Check FastAPI and PostgreSQL, then retry.",
          );
        const graph: UniverseGraph = await response.json();
        if (!controller.signal.aborted)
          store.getState().completeUniverse(token, graph);
      } catch (error) {
        if (!controller.signal.aborted)
          store
            .getState()
            .failUniverse(
              token,
              error instanceof Error
                ? error.message
                : "The atlas is unavailable.",
            );
      }
    },
    [store],
  );
}
