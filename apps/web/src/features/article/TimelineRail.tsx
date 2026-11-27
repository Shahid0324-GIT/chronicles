"use client";
import { useEffect, useRef } from "react";
import type { NarrativeJourney } from "@/features/narrative/contracts";
import SpoilerControl from "@/features/narrative/SpoilerControl";

export default function TimelineRail({
  journey,
  current,
  told,
  onSelect,
}: {
  journey: NarrativeJourney;
  current: string[];
  told: Map<string, string>;
  onSelect: (index: number) => void;
}) {
  const list = useRef<HTMLOListElement>(null);
  const first = journey.steps.findIndex((s) => current.includes(s.eventNodeId));
  // Keep the moment being read in view without scrolling the article itself.
  useEffect(() => {
    const box = list.current,
      item = box?.querySelector<HTMLElement>('[aria-current="true"]');
    if (!box || !item) return;
    // The list runs downwards beside the article and sideways on narrow screens.
    const top = item.parentElement!.offsetTop,
      left = item.parentElement!.offsetLeft;
    if (
      top < box.scrollTop ||
      top + item.offsetHeight > box.scrollTop + box.clientHeight
    )
      box.scrollTop = top - box.clientHeight / 3;
    if (
      left < box.scrollLeft ||
      left + item.offsetWidth > box.scrollLeft + box.clientWidth
    )
      box.scrollLeft = left - box.clientWidth / 3;
  }, [first]);
  return (
    <aside className="article-rail" aria-label="Arc timeline">
      <SpoilerControl />
      <h2>Timeline</h2>
      <ol ref={list}>
        {journey.steps.map((step, index) => {
          const active = current.includes(step.eventNodeId);
          return (
            <li
              key={step.id}
              className={active ? "active" : index < first ? "read" : undefined}
            >
              <button
                type="button"
                aria-current={active ? "true" : undefined}
                onClick={() => onSelect(index)}
              >
                <span>{step.title}</span>
                <small>
                  {step.episodeLabel}
                  {!told.has(step.eventNodeId) && " · event notes only"}
                </small>
              </button>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
