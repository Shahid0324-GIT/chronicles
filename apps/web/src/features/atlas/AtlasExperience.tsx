"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef } from "react";
import type { Universe, UniverseGraph } from "@/lib/contracts";
import {
  ExplorationProvider,
  useExploration,
  useExplorationApi,
} from "@/stores/ExplorationProvider";
import { useUniverseLoader } from "@/features/universe/useUniverseLoader";
import UniverseSwitcher from "@/features/universe/UniverseSwitcher";
import ContextPanel from "@/features/discovery/ContextPanel";
import JourneyControls from "@/features/journey/JourneyControls";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
import { filterGraph } from "@/features/graph/filter";
import Search from "./Search";
import MapControls from "./MapControls";
import LayerControls from "./LayerControls";
const GraphCanvas = dynamic(() => import("@/features/graph/GraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="canvas-status" role="status">
      Unfolding the atlas…
    </div>
  ),
});
export default function AtlasExperience({
  universes,
  graph,
}: {
  universes: Universe[];
  graph: UniverseGraph | null;
}) {
  return (
    <ExplorationProvider graph={graph}>
      <Experience universes={universes} />
    </ExplorationProvider>
  );
}
function Experience({ universes }: { universes: Universe[] }) {
  const root = useRef<HTMLElement>(null);
  const graph = useExploration((s) => s.graph),
    active = useExploration((s) => s.activeUniverse),
    status = useExploration((s) => s.status),
    error = useExploration((s) => s.error),
    mode = useExploration((s) => s.mode),
    setMode = useExploration((s) => s.setMode),
    continuity = useExploration((s) => s.continuityId),
    setContinuity = useExploration((s) => s.setContinuity),
    types = useExploration((s) => s.types),
    selected = useExploration((s) => s.selectedId),
    resetFilters = useExploration((s) => s.resetFilters);
  const store = useExplorationApi(),
    load = useUniverseLoader();
  const visible = useMemo(
    () => (graph ? filterGraph(graph, continuity, types) : null),
    [graph, continuity, types],
  );
  useAtlasMotion(root, active?.id);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      const editable =
        event.target instanceof HTMLElement &&
        (event.target.matches("input, select, textarea") ||
          event.target.isContentEditable);
      if (editable) return;
      if (event.key === "/") {
        event.preventDefault();
        root.current
          ?.querySelector<HTMLInputElement>('[aria-label="Search the atlas"]')
          ?.focus();
      }
      if (event.key === "Escape") store.getState().clearSelection();
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [store]);
  return (
    <section
      ref={root}
      className={[
        "atlas-app",
        selected ? "has-selection" : "",
        mode === "guided" ? "is-guided" : "",
      ].join(" ")}
      aria-label="Chronicles universe explorer"
    >
      <div className="map-texture" aria-hidden="true" />
      <header className="atlas-topbar glass entry-motion">
        <div className="chronicles-brand">
          <span aria-hidden="true">✧</span>
          <div>
            CHRONICLES<small>A FICTIONAL UNIVERSE ATLAS</small>
          </div>
        </div>
        <div className="topbar-divider" />
        <UniverseSwitcher universes={universes} load={load} />
        <Search />
        <div className="mode-switch" role="group" aria-label="Exploration mode">
          <button
            aria-pressed={mode === "explore"}
            onClick={() => setMode("explore")}
          >
            Explore
          </button>
          <button
            aria-pressed={mode === "guided"}
            onClick={() => setMode("guided")}
          >
            <span aria-hidden="true">⌁</span> Guided
          </button>
        </div>
      </header>
      <div className="atlas-caption entry-motion">
        <p className="eyebrow">
          A WORLD IN THE MAKING <span>✦</span>
        </p>
        <h1>
          {active?.title.split(" — ")[0] ?? "Uncharted worlds"}
          <span>Every connection is a doorway.</span>
        </h1>
        <div className="continuity-control">
          <span aria-hidden="true">◉</span>
          <select
            aria-label="Active continuity"
            value={continuity ?? "all"}
            onChange={(e) =>
              setContinuity(e.target.value === "all" ? null : e.target.value)
            }
          >
            <option value="all">All continuities</option>
            {graph?.continuities.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <p className="scope-label">
          {graph?.nodes.some((n) => n.metadata.illustrative === true)
            ? "ILLUSTRATIVE ATLAS · EARLY-STORY SPOILERS"
            : "LOCAL COLLECTION"}
        </p>
      </div>
      {graph && graph.nodes.length > 0 && <GraphCanvas data={graph} />}
      {status === "loading" && (
        <div className="canvas-status" role="status">
          <span className="status-symbol">✧</span>
          <h2>Unfolding a new world…</h2>
          <p>Opening its people, places, and connections.</p>
        </div>
      )}
      {status === "error" && (
        <div className="canvas-status" role="alert">
          <h2>This world is out of reach.</h2>
          <p>{error}</p>
          {active && (
            <button
              className="primary-button"
              onClick={() => void load(active)}
            >
              Try again ↗
            </button>
          )}
        </div>
      )}
      {status === "ready" && !graph && (
        <div className="canvas-status">
          <h2>Your atlas starts here.</h2>
          <p>Choose a universe above to begin exploring.</p>
          {universes[0] ? (
            <button
              className="primary-button"
              onClick={() => void load(universes[0])}
            >
              Enter {universes[0].title.split(" — ")[0]} ↗
            </button>
          ) : (
            <p>No universes have been added to this local collection.</p>
          )}
        </div>
      )}
      {graph && !visible?.nodes.length && status === "ready" && (
        <div className="canvas-status">
          <h2>
            {graph.nodes.length
              ? "Nothing in this layer."
              : "A world waiting to be charted."}
          </h2>
          <p>
            {graph.nodes.length
              ? "Enable more map layers to reveal its connections."
              : "No entries have been added to this universe yet."}
          </p>
          {graph.nodes.length > 0 && (
            <button className="primary-button" onClick={resetFilters}>
              Show all layers
            </button>
          )}
        </div>
      )}
      <ContextPanel />
      <JourneyControls />
      <div className="atlas-bottom entry-motion">
        <div className="map-meta">
          <span className="live-mark" />
          LOCAL ATLAS<span className="meta-divider">/</span>
          {visible?.nodes.length ?? 0} ENTRIES
          <span className="meta-divider">/</span>
          {visible?.edges.length ?? 0} THREADS
        </div>
        <p>
          Drag to wander <span>·</span> Scroll to look closer <span>·</span>{" "}
          Select a thread to follow
        </p>
        <MapControls />
      </div>
      <div className="layers-position entry-motion">
        <LayerControls />
      </div>
      <div className="map-compass" aria-hidden="true">
        <span>N</span>
        <svg viewBox="0 0 64 64">
          <path
            d="M32 5l8 27-8 27-8-27zM5 32l27-8 27 8-27 8z"
            fill="none"
            stroke="currentColor"
          />
          <path d="M32 5v54M5 32h54" stroke="currentColor" opacity=".4" />
        </svg>
        <small>NOT ALL PATHS ARE LINEAR</small>
      </div>
    </section>
  );
}
