"use client";
import { useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import {
  activeDiscovery,
  activeStep,
  activeThread,
} from "@/features/narrative/selectors";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
import MediaArtwork from "@/features/discovery/MediaArtwork";
import { resolveMedia } from "@/features/discovery/media-registry";
import { BRANCHES, eventRegion } from "./model";
import type { NarrativeCatalog } from "@/features/narrative/contracts";

export const DISCOVERY_LABELS = {
  established: "Established in the opening",
  interpretation: "Editorial interpretation",
  unresolved: "Unresolved in this scope",
};
export default function StoryBranches() {
  const graph = useExploration((s) => s.graph),
    catalog = useExploration((s) => s.narrative),
    step = useExploration(activeStep),
    continuity = useExploration((s) => s.continuityId),
    branch = useExploration((s) => s.expandedBranch),
    select = useExploration((s) => s.selectNode),
    enter = useExploration((s) => s.enterLore),
    discover = useExploration((s) => s.selectDiscovery),
    toggle = useExploration((s) => s.toggleBranch),
    thread = useExploration(activeThread),
    discovery = useExploration(activeDiscovery),
    mode = useExploration((s) => s.mode),
    sources = useExploration((s) => s.toggleSourceNotes);
  const root = useRef<HTMLElement>(null);
  useAtlasMotion(root, [branch, step?.id, discovery?.id].join(":"), "card");
  if (!graph || !step || !branch) return null;
  const region = eventRegion(graph, step, catalog, continuity),
    definition = BRANCHES.find((b) => b.kind === branch)!;
  const items = branch === "lore" ? [] : region[branch];
  const activeLore =
    branch === "lore" && mode === "lore" && thread && discovery;
  const catalogInvestigation =
    activeLore && !region.lore.some((item) => item.id === thread.id);
  return (
    <section
      className={
        "story-branch branch-" +
        branch +
        (catalogInvestigation ? " catalog-investigation" : "")
      }
      ref={root}
      aria-label={definition.label + " branch"}
    >
      <div className="branch-origin">
        <span>{definition.glyph}</span>
        <p>
          {definition.label}
          <small>
            {catalogInvestigation ? "JOURNEY BOOKMARK" : "FROM MOMENT"}{" "}
            {String(stepNumber(catalog, step.id)).padStart(2, "0")} ·{" "}
            {step.title}
          </small>
        </p>
        <button aria-label="Collapse branch" onClick={() => toggle(branch)}>
          ×
        </button>
      </div>
      {activeLore ? (
        <>
          <aside className="lore-reading" aria-label="Lore discovery">
            <p className={"discovery-class " + discovery.classification}>
              {DISCOVERY_LABELS[discovery.classification]}
            </p>
            <h2>{discovery.title}</h2>
            <p>{discovery.explanation}</p>
            <button className="text-link" onClick={sources}>
              Sources &amp; scope ↗
            </button>
            <button
              className="text-link inspect-discovery"
              onClick={() => select(discovery.nodeId)}
            >
              Inspect map entry ↗
            </button>
          </aside>
          <div className="discovery-path" aria-label="Connected discoveries">
            {thread.discoveryIds.map((id, i) => {
              const item = catalog.discoveries.find((d) => d.id === id);
              if (!item) return null;
              return (
                <button
                  key={id}
                  className={id === discovery.id ? "current" : ""}
                  onClick={() => discover(id)}
                  aria-label={
                    item.title + " · " + DISCOVERY_LABELS[item.classification]
                  }
                  aria-pressed={id === discovery.id}
                >
                  <span className={"discovery-seal " + item.classification}>
                    {i + 1}
                  </span>
                  <strong>{item.title}</strong>
                  <small>{DISCOVERY_LABELS[item.classification]}</small>
                </button>
              );
            })}
          </div>
        </>
      ) : (
        <div className="branch-entities">
          {branch === "lore"
            ? region.lore.map((item) => (
                <button
                  key={item.id}
                  onClick={() => enter(item.id)}
                  aria-label={"Investigate " + item.title}
                >
                  <span className="lore-seal">◎</span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>
                      {item.discoveryIds.length} connected discoveries
                    </small>
                  </span>
                  <span aria-hidden="true">↗</span>
                </button>
              ))
            : items.map((node) => (
                <button
                  key={node.id}
                  onClick={() => select(node.id)}
                  aria-label={"Inspect " + node.title}
                >
                  <MediaArtwork
                    asset={resolveMedia(node.id, node.type)}
                    className={
                      node.type === "CHARACTER"
                        ? "character-portrait"
                        : "entity-illustration"
                    }
                  />
                  <span>
                    <strong>{node.title}</strong>
                    <small>
                      {node.type.toLowerCase()}
                      {step.participantRoles?.find((r) => r.nodeId === node.id)
                        ?.role
                        ? " · " +
                          step.participantRoles.find(
                            (r) => r.nodeId === node.id,
                          )?.role
                        : ""}
                    </small>
                  </span>
                  <span aria-hidden="true">↗</span>
                </button>
              ))}
          {!region[branch].length && (
            <p className="quiet-note">
              No {definition.label.toLowerCase()} have been connected to this
              moment in the current collection.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
function stepNumber(catalog: NarrativeCatalog, stepId: string) {
  return (
    catalog.journeys.flatMap((j) => j.steps).findIndex((s) => s.id === stepId) +
    1
  );
}
