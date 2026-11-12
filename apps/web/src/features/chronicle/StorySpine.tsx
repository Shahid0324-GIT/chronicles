"use client";
import { useEffect, useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { activeJourney } from "@/features/narrative/selectors";
import MediaArtwork from "@/features/discovery/MediaArtwork";
import { resolveMedia } from "@/features/discovery/media-registry";
import { spineLayout } from "./model";
import { useAtlasMotion } from "@/animations/useAtlasMotion";

export default function StorySpine() {
  const journey = useExploration(activeJourney),
    index = useExploration((s) => s.journeyIndex),
    select = useExploration((s) => s.selectMilestone),
    upcoming = useExploration((s) => s.showUpcoming),
    graph = useExploration((s) => s.graph);
  const root = useRef<HTMLElement>(null);
  const keyboardNavigation = useRef(false);
  useEffect(() => {
    if (keyboardNavigation.current) {
      root.current
        ?.querySelector<HTMLButtonElement>('[aria-current="step"]')
        ?.focus({ preventScroll: true });
      keyboardNavigation.current = false;
    }
  }, [index]);
  useAtlasMotion(root, journey?.id, "mode");
  if (!journey || !graph) return null;
  const milestones = spineLayout(journey, index);
  return (
    <nav
      ref={root}
      className="story-spine"
      aria-label="Story milestones"
      onKeyDown={(e) => {
        const next =
          e.key === "ArrowRight"
            ? index + 1
            : e.key === "ArrowLeft"
              ? index - 1
              : e.key === "Home"
                ? 0
                : e.key === "End"
                  ? journey.steps.length - 1
                  : null;
        if (next !== null) {
          e.preventDefault();
          keyboardNavigation.current = true;
          select(Math.max(0, Math.min(journey.steps.length - 1, next)));
        }
      }}
    >
      <div className="spine-rule" aria-hidden="true">
        <span
          style={{
            width: (index / Math.max(1, journey.steps.length - 1)) * 100 + "%",
          }}
        />
      </div>
      <ol>
        {milestones.map(({ step, index: position, x, position: state }) => {
          const node = graph.nodes.find((n) => n.id === step.eventNodeId);
          if (!node) return null;
          const hidden = state === "upcoming" && !upcoming;
          return (
            <li
              key={step.id}
              className={"milestone " + state}
              style={{ left: x + "%" }}
            >
              <button
                onClick={() => select(position)}
                aria-current={state === "current" ? "step" : undefined}
                aria-label={
                  hidden
                    ? "Continue to moment " + (position + 1)
                    : "Open story moment " + (position + 1) + ": " + step.title
                }
              >
                <span className="milestone-status">
                  {state === "earlier"
                    ? "Earlier"
                    : state === "current"
                      ? "You are here"
                      : "Ahead"}
                </span>
                <span className="milestone-picture">
                  {hidden ? (
                    <span className="sealed-moment" aria-hidden="true">
                      ◇
                    </span>
                  ) : (
                    <MediaArtwork
                      asset={resolveMedia(node.id, node.type)}
                      priority={position === index}
                    />
                  )}
                  <span className="milestone-index">
                    {String(position + 1).padStart(2, "0")}
                  </span>
                </span>
                <span className="milestone-title">
                  {hidden ? "An unopened page" : step.title}
                </span>
                <small>
                  {hidden
                    ? "Select to continue"
                    : step.episodeLabel.replace("EPISODE ", "EP. ")}
                </small>
              </button>
              <span className="milestone-branch-mark" aria-hidden="true">
                {step.loreThreadIds.length ? "◇ · ◎" : "◇"}
              </span>
            </li>
          );
        })}
      </ol>
      <span className="spine-direction" aria-hidden="true">
        →
      </span>
    </nav>
  );
}
