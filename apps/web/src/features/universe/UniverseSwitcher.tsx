"use client";
import { useEffect, useRef, useState } from "react";
import type { Universe } from "@/lib/contracts";
import { useExploration } from "@/stores/ExplorationProvider";
import MediaArtwork from "@/features/discovery/MediaArtwork";
import { resolveMedia } from "@/features/discovery/media-registry";
export default function UniverseSwitcher({
  universes,
  load,
}: {
  universes: Universe[];
  load: (universe: Universe) => Promise<void>;
}) {
  const active = useExploration((s) => s.activeUniverse);
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  return (
    <div
      ref={root}
      className="universe-switcher"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setOpen(false);
          root.current?.querySelector("button")?.focus();
        }
      }}
    >
      <button
        className="world-switch"
        aria-expanded={open}
        aria-controls="universe-menu"
        onClick={() => setOpen(!open)}
      >
        <span className="eyebrow">YOUR UNIVERSE</span>
        <span>
          {active?.title.split(" — ")[0] ?? "Choose a universe"}
          <span aria-hidden="true">⌄</span>
        </span>
      </button>
      {open && (
        <div id="universe-menu" className="universe-menu glass">
          <p className="eyebrow">THE COLLECTION</p>
          {universes.map((universe) => (
            <button
              key={universe.id}
              aria-pressed={universe.id === active?.id}
              onClick={() => {
                setOpen(false);
                void load(universe);
              }}
            >
              <MediaArtwork asset={resolveMedia(universe.id)} />
              <span>
                <strong>{universe.title}</strong>
                <small>
                  {universe.id === active?.id
                    ? "Currently exploring"
                    : "Enter this universe"}
                </small>
              </span>
              <span aria-hidden="true">↗</span>
            </button>
          ))}
          {!universes.length && <p>No universes have been charted yet.</p>}
        </div>
      )}
    </div>
  );
}
