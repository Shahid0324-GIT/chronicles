"use client";
import { useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
import { deriveJourney } from "./journey";
export default function JourneyControls() {
  const mode = useExploration((s) => s.mode),
    graph = useExploration((s) => s.graph),
    continuity = useExploration((s) => s.continuityId),
    index = useExploration((s) => s.journeyIndex),
    step = useExploration((s) => s.stepJourney),
    setMode = useExploration((s) => s.setMode);
  const root = useRef<HTMLElement>(null);
  useAtlasMotion(root, `${mode}-${index}`, "mode");
  if (mode !== "guided" || !graph) return null;
  const result = deriveJourney(graph, continuity);
  return (
    <section
      ref={root}
      className="journey-controls glass"
      aria-label="Guided journey"
    >
      <span className="journey-emblem" aria-hidden="true">
        ⌁
      </span>
      {result.available ? (
        <>
          <div>
            <p className="eyebrow">
              GUIDED JOURNEY / {index + 1} OF {result.journey.nodeIds.length}
            </p>
            <h2>{result.journey.title}</h2>
            <progress
              value={index + 1}
              max={result.journey.nodeIds.length}
              aria-label="Journey progress"
            />
          </div>
          <button
            disabled={index === 0}
            onClick={() => step(-1)}
            aria-label="Previous event"
          >
            ←
          </button>
          <button
            disabled={index === result.journey.nodeIds.length - 1}
            onClick={() => step(1)}
            aria-label="Next event"
          >
            →
          </button>
        </>
      ) : (
        <div>
          <p className="eyebrow">A STORY STILL TO BE CHARTED</p>
          <h2>Connections are not a chronology.</h2>
          <p>{result.reason}</p>
        </div>
      )}
      <button className="text-button" onClick={() => setMode("explore")}>
        Explore freely ↗
      </button>
    </section>
  );
}
