"use client";
import { useExploration } from "@/stores/ExplorationProvider";
import { activeJourney } from "@/features/narrative/selectors";
import StorySpine from "./StorySpine";
import EventInvestigation from "./EventInvestigation";
import SourceNotes from "./SourceNotes";

export default function StoryCanvas() {
  const journey = useExploration(activeJourney),
    index = useExploration((s) => s.journeyIndex),
    upcoming = useExploration((s) => s.showUpcoming),
    toggle = useExploration((s) => s.toggleUpcoming),
    expanded = useExploration((s) => s.eventExpanded),
    back = useExploration((s) => s.backFocus),
    history = useExploration((s) => s.focusHistory.length),
    status = useExploration((s) => s.narrativeStatus),
    availability = useExploration((s) => s.narrative.availability),
    setMode = useExploration((s) => s.setMode);
  return (
    <section
      className={
        "chronicle-canvas " + (expanded ? "investigating" : "overview")
      }
      aria-label="Narrative atlas"
      tabIndex={0}
    >
      {journey ? (
        <>
          <header className="story-intro">
            <div>
              <p className="folio-eyebrow">
                <span>CHRONICLE</span>{" "}
                {availability?.kind === "generated"
                  ? "RESEARCHED JOURNEY"
                  : "A CURATED JOURNEY"}
              </p>
              <h1>{journey.title}</h1>
              <p>{journey.overview ?? journey.introduction}</p>
            </div>
            <div className="story-orientation">
              <span>
                {availability?.kind === "generated"
                  ? "SUPPORTING EPISODE SOURCES · PARTIAL ORDER"
                  : "ORIGINAL BROADCAST PRESENTATION"}
              </span>
              {availability?.kind === "generated" && availability.partial && (
                <small>
                  Incomplete knowledge · {availability.gapCount ?? 0} ordering
                  gaps
                </small>
              )}
              <p>
                <span>Earlier</span>
                <b>Moment {String(index + 1).padStart(2, "0")}</b>
                <span>Ahead</span>
              </p>
              <label>
                <input type="checkbox" checked={upcoming} onChange={toggle} />
                Preview upcoming details
              </label>
            </div>
          </header>
          <StorySpine />
          <EventInvestigation />
          <SourceNotes />
          <footer className="story-footnote">
            <button disabled={!history} onClick={back}>
              ← Back to previous focus
            </button>
            <p>{journey.spoilerScope}</p>
            <span>CHRONICLES / {String(index + 1).padStart(2, "0")}</span>
          </footer>
        </>
      ) : (
        <div className="chronicle-unavailable" role="status">
          <span aria-hidden="true">◇</span>
          <h1>
            {status === "loading"
              ? "Opening the chronicle…"
              : "A story waiting to be charted."}
          </h1>
          <p>
            {status === "error"
              ? "The story notes could not be opened. The local graph remains available."
              : "Choose a supported continuity, or explore the collection freely."}
          </p>
          <button onClick={() => setMode("explore")}>
            Open the free graph ↗
          </button>
        </div>
      )}
    </section>
  );
}
