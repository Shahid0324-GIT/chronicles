"use client";
import { useEffect, useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import {
  activeDiscovery,
  activeJourney,
  activeStep,
  activeThread,
} from "@/features/narrative/selectors";
import { resolveMedia } from "@/features/discovery/media-registry";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
export default function SourceNotes() {
  const open = useExploration((s) => s.sourceNotesOpen),
    toggle = useExploration((s) => s.toggleSourceNotes),
    step = useExploration(activeStep),
    discovery = useExploration(activeDiscovery),
    mode = useExploration((s) => s.mode),
    journey = useExploration(activeJourney),
    thread = useExploration(activeThread),
    catalog = useExploration((s) => s.narrative);
  const root = useRef<HTMLElement>(null),
    close = useRef<HTMLButtonElement>(null);
  useAtlasMotion(root, open, "card");
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement;
    close.current?.focus({ preventScroll: true });
    return () => {
      if (previous instanceof HTMLElement && previous.isConnected)
        previous.focus({ preventScroll: true });
    };
  }, [open]);
  const item = mode === "lore" ? discovery : step;
  if (!open || !item) return null;
  const asset = resolveMedia(
    "eventNodeId" in item ? item.eventNodeId : item.nodeId,
  );
  return (
    <aside
      ref={root}
      className="source-notebook"
      aria-label="Source notes"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          toggle();
        }
      }}
    >
      <header>
        <span className="folio-eyebrow">THE MARGINALIA</span>
        <button ref={close} onClick={toggle} aria-label="Close source notes">
          ×
        </button>
      </header>
      <h2>Notes behind the story</h2>
      <p>{mode === "lore" ? thread?.spoilerScope : journey?.spoilerScope}</p>
      <p>
        {catalog.availability?.kind === "generated"
          ? "Source-backed model research with evidence-gated publication. Assessments are not independent verification."
          : "Manually curated introductory notes. No automated research."}
      </p>
      {mode !== "lore" && <p>{journey?.ordering.explanation}</p>}
      <ol>
        {catalog.sources
          .filter((source) => item.sourceIds.includes(source.id))
          .map((source) => (
            <li key={source.id}>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.title} ↗
              </a>
              <small>{source.locator}</small>
            </li>
          ))}
      </ol>
      <footer>
        <strong>About the illustration</strong>
        <p>{asset.credit}</p>
        {asset.sourceUrl && (
          <a href={asset.sourceUrl} target="_blank" rel="noreferrer">
            Image source ↗
          </a>
        )}
      </footer>
    </aside>
  );
}
