"use client";
import { useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { useAtlasMotion } from "@/animations/useAtlasMotion";
import { activeJourney, activeStep, activeThread } from "./selectors";
export default function NarrativeDock() {
  const graph = useExploration((s) => s.graph),
    mode = useExploration((s) => s.mode),
    index = useExploration((s) => s.journeyIndex),
    advance = useExploration((s) => s.stepJourney),
    resume = useExploration((s) => s.resumeJourney),
    begin = useExploration((s) => s.beginJourney),
    status = useExploration((s) => s.narrativeStatus),
    setMode = useExploration((s) => s.setMode),
    continuity = useExploration((s) => s.continuityId);
  const journey = useExploration(activeJourney),
    step = useExploration(activeStep),
    thread = useExploration(activeThread);
  const root = useRef<HTMLElement>(null);
  useAtlasMotion(root, [mode, index, journey?.id, status].join(":"), "mode");
  if (!graph) return null;
  if (!journey)
    return mode === "guided" ? (
      <section
        ref={root}
        className="journey-controls narrative-dock glass"
        aria-label="Guided journey"
      >
        <div>
          <p className="eyebrow">THE INTRODUCTION IS UNAVAILABLE</p>
          <h2>
            {status === "loading"
              ? "Opening the story notes…"
              : "A few story threads are missing."}
          </h2>
          <p>
            {!continuity
              ? "Choose a continuity to follow its story."
              : status === "error"
                ? "The narrative notes could not be opened. The map remains available."
                : "This map does not contain all the entries needed for the curated introduction."}
          </p>
        </div>
        <button onClick={() => setMode("explore")}>Explore freely ↗</button>
      </section>
    ) : null;
  const paused = mode !== "guided",
    completed = index === journey.steps.length - 1;
  return (
    <section
      ref={root}
      className="journey-controls narrative-dock glass"
      aria-label="Guided journey"
    >
      <div className="journey-counter">
        <strong>{String(index + 1).padStart(2, "0")}</strong>
        <span>/ {String(journey.steps.length).padStart(2, "0")}</span>
      </div>
      <div className="journey-heading">
        <p className="eyebrow">
          {paused
            ? "JOURNEY PAUSED"
            : completed
              ? "INTRODUCTION COMPLETE"
              : "ORIGINAL BROADCAST · A CURATED INTRODUCTION"}
        </p>
        <h2>{step?.title}</h2>
        <progress
          value={index + 1}
          max={journey.steps.length}
          aria-label="Journey progress"
        />
        <small>
          {paused && mode === "lore"
            ? "Investigating " + thread?.title
            : journey.title}
        </small>
      </div>
      {paused ? (
        <button className="resume-journey" onClick={resume}>
          Return to journey ↗
        </button>
      ) : (
        <div className="journey-arrows">
          <button
            disabled={index === 0}
            onClick={() => advance(-1)}
            aria-label="Previous story moment"
          >
            ←
          </button>
          <button
            disabled={completed}
            onClick={() => advance(1)}
            aria-label="Next story moment"
          >
            →
          </button>
          {completed && (
            <button
              className="restart-journey"
              onClick={() => begin(journey.id, true)}
            >
              Begin again
            </button>
          )}
        </div>
      )}
    </section>
  );
}
