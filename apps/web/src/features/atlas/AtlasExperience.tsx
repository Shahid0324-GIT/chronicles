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
import StoryCanvas from "@/features/chronicle/StoryCanvas";
import { themeForUniverse, themeStyle } from "@/features/chronicle/design";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
import { filterGraph } from "@/features/graph/filter";
import Search from "./Search";
import MapControls from "./MapControls";
import LayerControls from "./LayerControls";
import ResearchControls from "@/features/research/ResearchControls";
import { readerGraph } from "@/features/narrative/reader-graph";
import ReaderControls from "@/features/narrative/ReaderControls";
const GraphCanvas = dynamic(() => import("@/features/graph/GraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="canvas-status" role="status">
      Unfolding the graph…
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
  const canonicalGraph = useExploration((s) => s.graph),
    active = useExploration((s) => s.activeUniverse),
    status = useExploration((s) => s.status),
    error = useExploration((s) => s.error),
    mode = useExploration((s) => s.mode),
    setMode = useExploration((s) => s.setMode),
    continuity = useExploration((s) => s.continuityId),
    setContinuity = useExploration((s) => s.setContinuity),
    types = useExploration((s) => s.types),
    selected = useExploration((s) => s.selectedId),
    resetFilters = useExploration((s) => s.resetFilters),
    layout = useExploration((s) => s.layoutKind),
    narrativeStatus = useExploration((s) => s.narrativeStatus);
  const catalog = useExploration((s) => s.narrative),
    boundary = useExploration((s) => s.spoilerPosition);
  const graph = useMemo(
    () =>
      canonicalGraph ? readerGraph(canonicalGraph, catalog, boundary) : null,
    [canonicalGraph, catalog, boundary],
  );
  const store = useExplorationApi(),
    load = useUniverseLoader();
  const visible = useMemo(
    () => (graph ? filterGraph(graph, continuity, types) : null),
    [graph, continuity, types],
  );
  const story =
    layout !== "free" ||
    mode !== "explore" ||
    narrativeStatus === "idle" ||
    narrativeStatus === "loading";
  const theme = themeForUniverse(active?.slug);
  useAtlasMotion(root, active?.id);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (
        event.target instanceof HTMLElement &&
        (event.target.matches("input, select, textarea") ||
          event.target.isContentEditable)
      )
        return;
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
      style={themeStyle(theme)}
      data-theme={theme.id}
      data-motif={theme.motif}
      className={[
        "atlas-app",
        "chronicle-shell",
        story ? "story-view" : "free-view",
        selected ? "has-selection" : "",
        mode === "guided" ? "is-guided" : mode === "lore" ? "is-lore" : "",
      ].join(" ")}
      aria-label="Chronicles universe explorer"
    >
      <div className="chronicle-atmosphere" aria-hidden="true" />
      <header className="atlas-topbar entry-motion">
        <div className="chronicles-brand">
          <svg viewBox="0 0 48 48" aria-hidden="true">
            <path
              d="M24 2l5 17 17 5-17 5-5 17-5-17-17-5 17-5zM24 9v30M9 24h30"
              fill="none"
              stroke="currentColor"
            />
            <circle cx="24" cy="24" r="15" fill="none" stroke="currentColor" />
          </svg>
          <div>
            Chronicles<small>AN ATLAS OF STORIES</small>
          </div>
        </div>
        <div className="header-world">
          <UniverseSwitcher universes={universes} load={load} />
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
        <nav className="mode-switch" aria-label="Exploration mode">
          <button
            aria-label="Guided"
            aria-pressed={mode !== "lore" && story}
            onClick={() => setMode("guided")}
          >
            <span aria-hidden="true">▤</span> Story map
          </button>
          <button
            aria-label="Lore"
            aria-pressed={mode === "lore" && story}
            onClick={() => setMode("lore")}
          >
            <span aria-hidden="true">◎</span> Lore
          </button>
          <button
            aria-label="Explore"
            aria-pressed={!story}
            onClick={() => setMode("explore")}
          >
            <span aria-hidden="true">⌘</span> Free graph
          </button>
        </nav>
        <Search />
        <ResearchControls />
      </header>
      {graph && status === "ready" && <ReaderControls />}
      {graph &&
        status === "ready" &&
        (story ? <StoryCanvas /> : <GraphCanvas data={graph} />)}
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
          {universes[0] ? (
            <button
              className="primary-button"
              onClick={() => void load(universes[0])}
            >
              Enter {universes[0].title} ↗
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
      {!story && (
        <>
          <div className="atlas-bottom">
            <div className="map-meta">
              LOCAL ATLAS / {visible?.nodes.length ?? 0} ENTRIES /{" "}
              {visible?.edges.length ?? 0} THREADS
            </div>
            <p>Drag to wander · Scroll to look closer</p>
            <MapControls />
          </div>
          <div className="layers-position">
            <LayerControls />
          </div>
        </>
      )}
    </section>
  );
}
