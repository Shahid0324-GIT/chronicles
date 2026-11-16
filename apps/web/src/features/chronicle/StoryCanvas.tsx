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
    unplaced = useExploration((s) => s.narrative.unorderedMilestones),
    coverage = useExploration((s) => s.narrative.coverage),
    entries = useExploration((s) => s.narrative.entryIndex),
    research = useExploration((s) => s.narrative.researchState),
    scope = useExploration((s) => s.narrative.researchScopes?.[0]),
    inspect = useExploration((s) => s.selectNode),
    setMode = useExploration((s) => s.setMode);
  return (
    <section
      className={
        "chronicle-canvas " + (expanded ? "investigating" : "overview")
      }
      aria-label="Narrative atlas"
      tabIndex={0}
    >
      {coverage && (
        <p className="reader-coverage" role="status">
          {coverage.acceptedEvents
            ? `Partially researched · ${coverage.acceptedEvents} accepted event${coverage.acceptedEvents === 1 ? "" : "s"} · ${coverage.validatedMilestones} validated event accounts`
            : research?.status === "queued" || research?.status === "running"
              ? "Research in progress"
              : coverage.entries
                ? `Partially researched · ${coverage.entries} source-backed entries · story events not established`
                : research?.coverage === "BLOCKED_BY_SOURCE_ACCESS"
                  ? "Research blocked by source access"
                  : research?.status === "partial" ||
                      research?.status === "completed"
                    ? "Research returned insufficient event evidence"
                    : "No verified story events at this boundary"}
          {research?.status === "failed" &&
            " · Research failed; open research details"}
        </p>
      )}
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
              {journey.presentationState &&
                journey.presentationState.status !== "validated" && (
                  <p role="status">{journey.presentationState.reason}</p>
                )}
            </div>
            <div className="story-orientation">
              <span>
                {availability?.kind === "generated"
                  ? `${journey.ordering.basis === "manga-chapter" ? "MANGA CHAPTER" : "SUPPORTING"} SOURCES · PARTIAL ORDER`
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
      ) : !unplaced?.length ? (
        <div className="chronicle-unavailable" role="status">
          <span aria-hidden="true">◇</span>
          <h1>
            {status === "loading"
              ? "Opening the chronicle…"
              : scope
                ? scope.title
                : entries?.length
                  ? "An arc taking shape"
                  : "A story waiting to be charted."}
          </h1>
          {scope && (
            <p>
              Manga chapters {scope.firstPosition}–{scope.lastPosition} ·
              research scope
            </p>
          )}
          <p>
            {status === "error"
              ? "The story notes could not be opened. The local graph remains available."
              : entries?.length
                ? "Verified encyclopedia content is available. The arc account is not ready."
                : "Choose a supported continuity, or explore the collection freely."}
          </p>
          <button onClick={() => setMode("explore")}>
            Open the free graph ↗
          </button>
          {!!entries?.length && (
            <nav aria-label="Available researched entries">
              {entries.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => inspect(entry.id, "inspection")}
                >
                  {entry.displayTitle} ↗
                </button>
              ))}
            </nav>
          )}
        </div>
      ) : null}
      {!!unplaced?.length && (
        <section
          className="unplaced-events"
          aria-label="Verified events with unresolved order"
        >
          <h2>Verified events · order unresolved</h2>
          <p>
            These events have accepted evidence. Their position in the story has
            not been established.
          </p>
          {unplaced.map((step) => (
            <article key={step.id}>
              <button onClick={() => inspect(step.eventNodeId, "inspection")}>
                {step.title}
              </button>
              <p>{step.body}</p>
              <small>{step.presentationState?.reason}</small>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
