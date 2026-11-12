"use client";
import { useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { activeJourney, activeStep } from "@/features/narrative/selectors";
import MediaArtwork from "@/features/discovery/MediaArtwork";
import { resolveMedia } from "@/features/discovery/media-registry";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
import type { JourneyStep } from "@/features/narrative/contracts";
import {
  BRANCHES,
  eventRegion,
  spineLayout,
  type EventConnection,
} from "./model";
import StoryBranches from "./StoryBranches";

export default function EventInvestigation() {
  const graph = useExploration((s) => s.graph),
    catalog = useExploration((s) => s.narrative),
    continuity = useExploration((s) => s.continuityId),
    step = useExploration(activeStep),
    journey = useExploration(activeJourney),
    index = useExploration((s) => s.journeyIndex),
    expanded = useExploration((s) => s.eventExpanded),
    expand = useExploration((s) => s.setEventExpanded),
    branch = useExploration((s) => s.expandedBranch),
    toggle = useExploration((s) => s.toggleBranch),
    select = useExploration((s) => s.selectMilestone),
    inspect = useExploration((s) => s.selectNode),
    notes = useExploration((s) => s.toggleSourceNotes),
    upcoming = useExploration((s) => s.showUpcoming);
  const root = useRef<HTMLDivElement>(null);
  useAtlasMotion(root, step?.id, "card");
  if (!graph || !step || !journey) return null;
  const node = graph.nodes.find((n) => n.id === step.eventNodeId);
  if (!node) return null;
  const region = eventRegion(graph, step, catalog, continuity);
  const origin =
    (spineLayout(journey, index).find((item) => item.index === index)?.x ??
      50) * 10;
  return (
    <div
      ref={root}
      className={"event-investigation " + (expanded ? "expanded" : "overview")}
    >
      {expanded && (
        <svg
          className="event-connection-stem"
          viewBox="0 0 1000 40"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path
            d={
              "M" +
              origin +
              " 0 V10 Q" +
              origin +
              " 20 " +
              (origin + 500) / 2 +
              " 20 T500 32 V40"
            }
          />
        </svg>
      )}
      <div className="event-composition">
        {expanded && (
          <CausalWing
            kind="causes"
            connections={region.causes}
            adjacent={journey.steps[index - 1]}
            openAdjacent={() => select(index - 1)}
            inspect={inspect}
          />
        )}
        <aside className="event-anchor" aria-label="Journey story">
          <div className="event-scene">
            <MediaArtwork
              asset={resolveMedia(node.id, node.type)}
              variant="scene"
              priority
            />
            <span className="scene-annotation">
              {String(index + 1).padStart(2, "0")} /{" "}
              {String(journey.steps.length).padStart(2, "0")}
            </span>
            <span className="scene-caption">INTERPRETIVE ATLAS ART</span>
          </div>
          <div className="event-prose">
            <p className="folio-eyebrow">{step.episodeLabel}</p>
            <h2>{step.title}</h2>
            <p>{step.body}</p>
            <div className="event-text-actions">
              <button onClick={() => expand(!expanded)}>
                {expanded ? "Return to overview ↑" : "Explore this moment ↓"}
              </button>
              <button onClick={notes}>Sources &amp; scope ↗</button>
            </div>
          </div>
        </aside>
        {expanded && (
          <CausalWing
            kind="consequences"
            connections={region.consequences}
            adjacent={upcoming ? journey.steps[index + 1] : undefined}
            openAdjacent={() => select(index + 1)}
            inspect={inspect}
          />
        )}
      </div>
      <div
        className="branch-index"
        role="group"
        aria-label="Explore event branches"
      >
        <span className="branch-index-label">THREADS IN THIS MOMENT</span>
        {BRANCHES.map(({ kind, label, glyph }) => (
          <button
            key={kind}
            disabled={!region[kind].length}
            aria-expanded={branch === kind}
            onClick={() => toggle(kind)}
          >
            <span aria-hidden="true">{glyph}</span>
            {label}
            <small>{region[kind].length}</small>
            <span aria-hidden="true">{branch === kind ? "−" : "+"}</span>
          </button>
        ))}
      </div>
      <StoryBranches />
    </div>
  );
}
function CausalWing({
  kind,
  connections,
  adjacent,
  openAdjacent,
  inspect,
}: {
  kind: "causes" | "consequences";
  connections: EventConnection[];
  adjacent?: JourneyStep;
  openAdjacent: () => void;
  inspect: (id: string) => void;
}) {
  return (
    <section
      className={"causal-wing " + kind}
      aria-label={kind === "causes" ? "Causes" : "Consequences"}
    >
      <h3>
        <span aria-hidden="true">{kind === "causes" ? "↳" : "↗"}</span>
        {kind === "causes" ? "Causes" : "Consequences"}
      </h3>
      {connections.length ? (
        connections.map(({ node, edge }) => (
          <button
            className="causal-link"
            key={edge.id}
            onClick={() => inspect(node.id)}
          >
            <strong>{node.title}</strong>
            <span>{edge.description}</span>
          </button>
        ))
      ) : (
        <p className="quiet-note">
          No explicit causal relationship is recorded for this moment.
        </p>
      )}
      {adjacent && (
        <div className="sequence-neighbor">
          <p className="folio-eyebrow">
            {kind === "causes" ? "EARLIER" : "LATER"} IN THE TELLING
          </p>
          <button onClick={openAdjacent}>
            <span className="sequence-diamond" aria-hidden="true">
              ◇
            </span>
            {adjacent.title}
            <span aria-hidden="true">→</span>
          </button>
          <small>Story sequence · not a causal claim</small>
        </div>
      )}
    </section>
  );
}
