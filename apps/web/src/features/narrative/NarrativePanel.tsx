"use client";
import { useEffect, useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { useAtlasMotion, useExitMotion } from "@/animations/useAtlasMotion";
import IconButton from "@/components/ui/IconButton";
import MediaArtwork from "@/features/discovery/MediaArtwork";
import { resolveMedia } from "@/features/discovery/media-registry";
import {
  activeJourney,
  activeStep,
  activeThread,
  activeDiscovery,
} from "./selectors";
const labels = {
  established: "Established in the opening",
  interpretation: "Editorial interpretation",
  unresolved: "Unresolved in this scope",
};
export default function NarrativePanel() {
  const mode = useExploration((s) => s.mode),
    graph = useExploration((s) => s.graph),
    narrative = useExploration((s) => s.narrative),
    index = useExploration((s) => s.journeyIndex),
    minimized = useExploration((s) => s.panelMinimized),
    minimize = useExploration((s) => s.minimizePanel),
    select = useExploration((s) => s.selectNode),
    discover = useExploration((s) => s.selectDiscovery),
    enter = useExploration((s) => s.enterLore),
    clear = useExploration((s) => s.clearSelection);
  const journey = useExploration(activeJourney),
    step = useExploration(activeStep),
    thread = useExploration(activeThread),
    discovery = useExploration(activeDiscovery);
  const key = [mode, step?.id, discovery?.id, minimized].join(":");
  const root = useRef<HTMLElement>(null),
    heading = useRef<HTMLHeadingElement>(null);
  useAtlasMotion(root, key, "card");
  const close = useExitMotion(
    root,
    () => {
      clear();
      document
        .querySelector<HTMLElement>('[aria-label="Interactive universe map"]')
        ?.focus({ preventScroll: true });
    },
    key,
  );
  useEffect(() => {
    if (root.current) root.current.scrollTop = 0;
    if (mode !== "explore" && !minimized)
      heading.current?.focus({ preventScroll: true });
  }, [key, mode, minimized]);
  const item =
    mode === "guided" ? step : mode === "lore" ? discovery : undefined;
  const nodeId = mode === "guided" ? step?.eventNodeId : discovery?.nodeId;
  const node = graph?.nodes.find((n) => n.id === nodeId);
  if (!item || !node || !graph) return null;
  const title = item.title,
    body = mode === "guided" ? step?.body : discovery?.explanation;
  const sourceIds = item.sourceIds,
    asset = resolveMedia(node.id, node.type);
  const related = item.presentation.relatedNodeIds
    .map((id) => graph.nodes.find((n) => n.id === id))
    .filter((n) => Boolean(n));
  const loreTargets =
    mode === "guided"
      ? narrative.loreThreads.filter((t) => step?.loreThreadIds.includes(t.id))
      : [];
  return (
    <aside
      ref={root}
      className={[
        "context-panel",
        "glass",
        "narrative-panel",
        minimized ? "minimized" : "",
      ].join(" ")}
      aria-label={mode === "guided" ? "Journey story" : "Lore discovery"}
    >
      <div className="panel-actions">
        <span className="eyebrow">
          {mode === "guided"
            ? "MOMENT " + String(index + 1).padStart(2, "0")
            : "◎ LORE INVESTIGATION"}
        </span>
        <div>
          <IconButton
            label={
              minimized ? "Expand narrative panel" : "Minimize narrative panel"
            }
            onClick={minimize}
          >
            {minimized ? "＋" : "−"}
          </IconButton>
          <IconButton label="Close narrative panel" onClick={close}>
            ×
          </IconButton>
        </div>
      </div>
      {!minimized && (
        <div className="narrative-art">
          <MediaArtwork asset={asset} className="context-art" />
          <span className="chapter-stamp">
            {mode === "guided" ? String(index + 1).padStart(2, "0") : "◎"}
          </span>
        </div>
      )}
      <div className="context-copy">
        {mode === "guided" && <p className="eyebrow">{step?.episodeLabel}</p>}
        {mode === "lore" && discovery && (
          <p className={"discovery-class " + discovery.classification}>
            {labels[discovery.classification]}
          </p>
        )}
        <h2 ref={heading} tabIndex={-1}>
          {title}
        </h2>
        {!minimized && (
          <>
            <p className="node-summary">{body}</p>
            <p className="canonical-reference">MAP ENTRY · {node.title}</p>
            <div className="related-entities">
              <p className="eyebrow">IN THIS MOMENT</p>
              {related.map(
                (entity) =>
                  entity && (
                    <button key={entity.id} onClick={() => select(entity.id)}>
                      <span aria-hidden="true">
                        {entity.type === "CHARACTER" ? "✧" : "◇"}
                      </span>{" "}
                      Inspect {entity.title}
                      <span aria-hidden="true">↗</span>
                    </button>
                  ),
              )}
            </div>
            {loreTargets.map((target) => (
              <button
                key={target.id}
                className="lore-prompt"
                onClick={() => enter(target.id)}
              >
                ◎ Investigate {target.title}
                <span aria-hidden="true">↗</span>
              </button>
            ))}
            {mode === "lore" && discovery && (
              <div className="related-discoveries">
                <p className="eyebrow">FOLLOW THE QUESTION</p>
                {discovery.relatedDiscoveryIds.map((id) => {
                  const next = narrative.discoveries.find((d) => d.id === id);
                  return (
                    next && (
                      <button key={id} onClick={() => discover(id)}>
                        <span
                          className={"discovery-dot " + next.classification}
                          aria-hidden="true"
                        />
                        <span>
                          {next.title}
                          <small>{labels[next.classification]}</small>
                        </span>
                        <span aria-hidden="true">↗</span>
                      </button>
                    )
                  );
                })}
              </div>
            )}
            <details className="narrative-sources">
              <summary>Scope, sources &amp; artwork</summary>
              <p>
                {mode === "guided"
                  ? journey?.spoilerScope
                  : thread?.spoilerScope}
              </p>
              <p>Manually curated introductory notes. No automated research.</p>
              {narrative.sources
                .filter((s) => sourceIds.includes(s.id))
                .map((source) => (
                  <a
                    key={source.id}
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {source.title}
                    <small>{source.locator}</small>
                  </a>
                ))}
              <p>{asset.credit}</p>
            </details>
          </>
        )}
      </div>
    </aside>
  );
}
