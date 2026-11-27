"use client";
import { Fragment, useEffect, useRef, useState } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import type { NarrativeJourney } from "@/features/narrative/contracts";
import { DRAFT_NOTE, isDraftWorld } from "@/features/narrative/draft";
import { usePositionUnit } from "@/features/narrative/units";
import JourneyTree from "./JourneyTree";
import Motif from "./Motif";
import { journeyStops, momentsAt, sectionsAt } from "./journey";
import { eventsAt, paragraphKey, readingIndex, readingMinutes } from "./model";

export interface ReadingPlace {
  /** The stop the reader chose; null follows their place on the story map. */
  stop: number | null;
  straight: boolean;
}

/**
 * One arc as a journey: a cinematic opening, the tree of stops and moments, and the
 * story told stop by stop or straight through. Names open their page beside the text.
 */
export default function ArticleView({
  journey,
  place,
  onPlace,
}: {
  journey: NarrativeJourney;
  place: ReadingPlace;
  onPlace: (place: ReadingPlace) => void;
}) {
  const story = journey.story ?? [],
    sources = useExploration((s) => s.narrative.sources),
    relations = useExploration((s) => s.narrative.relations),
    entries = useExploration((s) => s.narrative.entryIndex),
    inspect = useExploration((s) => s.selectNode),
    selectMilestone = useExploration((s) => s.selectMilestone),
    limit = useExploration((s) => s.spoilerPosition),
    setLimit = useExploration((s) => s.setSpoilerPosition),
    selected = useExploration((s) => s.selectedId),
    panel = useExploration((s) => s.mode === "explore" && !!s.selectedId),
    draft = useExploration((s) => isDraftWorld(s.graph?.universe.slug)),
    step = useExploration((s) => journey.steps[s.journeyIndex]);
  const unit = usePositionUnit();
  const root = useRef<HTMLDivElement>(null);
  const opened = useRef<HTMLElement | null>(null);
  const [asking, setAsking] = useState<number | null>(null);
  const [reading, setReading] = useState<number | null>(null);
  const stops = journeyStops(journey);
  const reached = stops.filter((s) => !s.hidden);
  const chosen =
    reached.find((s) => s.position === (place.stop ?? step?.position)) ??
    reached.at(-1) ??
    stops[0];
  // While reading straight through, the tree follows the text.
  const marked = (place.straight && reading) || chosen?.position || 0;
  const moments = momentsAt(journey.steps, marked);
  const causes = (relations ?? []).filter(
    (r) => r.type === "CAUSED" || r.type === "ENABLED",
  );
  const sections = place.straight
    ? story.map((s, index) => ({ ...s, index }))
    : sectionsAt(
        story,
        new Set(
          momentsAt(journey.steps, chosen?.position ?? 0).map(
            (m) => m.eventNodeId,
          ),
        ),
      );
  const cited = new Set(
    story.flatMap((s) => s.paragraphs.flatMap((p) => p.sourceIds)),
  );
  const references = sources.filter((s) => cited.has(s.id));
  const cast = [
    ...new Set(
      sections.flatMap((s) =>
        s.paragraphs.flatMap((p) =>
          p.segments.flatMap((g) => (g.nodeId ? [g.nodeId] : [])),
        ),
      ),
    ),
  ].slice(0, 12);

  const open = (id: string, from: HTMLElement | null) => {
    opened.current = from;
    inspect(id, "inspection");
  };

  const choose = (position: number) => {
    const stop = stops.find((s) => s.position === position);
    if (!stop) return;
    if (stop.hidden) {
      setAsking(position);
      return;
    }
    setAsking(null);
    setReading(null);
    onPlace({ stop: position, straight: false });
    // The story map keeps the same moment.
    const first = journey.steps.findIndex((s) => s.position === position);
    if (first >= 0) selectMilestone(first);
  };

  useEffect(() => {
    if (!place.straight) return;
    const scroller = root.current?.closest<HTMLElement>(".chronicle-canvas");
    if (!scroller) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      const paragraphs = [
        ...(root.current?.querySelectorAll<HTMLElement>("[data-paragraph]") ??
          []),
      ];
      const line =
        scroller.getBoundingClientRect().top + scroller.clientHeight * 0.35;
      const at = readingIndex(
        paragraphs.map((p) => p.getBoundingClientRect().top),
        line,
        false,
      );
      const events = eventsAt(
        journey.story ?? [],
        paragraphs[at]?.dataset.paragraph ?? "",
      );
      const position = journey.steps.find((s) =>
        events.includes(s.eventNodeId),
      )?.position;
      if (position) setReading(position);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    scroller.addEventListener("scroll", schedule, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      scroller.removeEventListener("scroll", schedule);
    };
  }, [place.straight, journey]);

  // Closing a page returns the keyboard to what opened it.
  useEffect(() => {
    if (!selected && opened.current?.isConnected) {
      opened.current.focus({ preventScroll: true });
      opened.current = null;
    }
  }, [selected]);

  if (!chosen) return null;
  // Reading straight through, the heading and the arrows follow the reader.
  const current = reached.find((s) => s.position === marked) ?? chosen;
  const index = reached.indexOf(current);
  const next = stops[stops.indexOf(current) + 1];
  return (
    <div ref={root} className="article-view" data-panel={panel}>
      <header className="story-hero">
        <div>
          <p className="story-kicker">
            {draft ? "AI draft awaiting review" : "Story arc"} ·{" "}
            {readingMinutes(story)} min read
          </p>
          <h1>{journey.title}</h1>
          <p className="story-lead">
            {journey.overview ?? journey.introduction}
          </p>
          <div className="story-actions">
            <button
              type="button"
              className="story-primary"
              onClick={() => {
                const still = window.matchMedia(
                  "(prefers-reduced-motion: reduce)",
                ).matches;
                root.current
                  ?.querySelector(".journey-block")
                  ?.scrollIntoView({ behavior: still ? "auto" : "smooth" });
              }}
            >
              Begin the journey
            </button>
            <span>
              {journey.steps.length} moments · {stops.length} {unit}
              {stops.length === 1 ? "" : "s"}
            </span>
          </div>
          {draft && <p className="story-note">{DRAFT_NOTE}</p>}
        </div>
        <Motif kind={journey.theme?.motif ?? "rings"} />
      </header>

      <div className="journey-block">
        <JourneyTree
          stops={stops}
          moments={moments}
          chosen={marked}
          unit={unit}
          causes={causes}
          onStop={choose}
          onMoment={(id) => open(id, null)}
        />
        {asking !== null && (
          <div className="reveal-ask" role="alert">
            <span>
              Reveal the story up to {unit} {asking}? It shows everything before
              it too.
            </span>
            <button
              type="button"
              className="story-primary"
              onClick={() => {
                onPlace({ stop: asking, straight: false });
                setAsking(null);
                setLimit(asking);
              }}
            >
              Reveal
            </button>
            <button type="button" onClick={() => setAsking(null)}>
              Keep hidden
            </button>
          </div>
        )}
        <p className="journey-hint">
          {limit === null
            ? "Everything is visible."
            : `Nothing after ${unit} ${limit} is shown.`}{" "}
          Drag to travel along the map; choose a moment to open it.
          {limit !== null && (
            <button type="button" onClick={() => setLimit(null)}>
              Show everything
            </button>
          )}
        </p>
      </div>

      <div className="stop-header">
        <div>
          <p className="story-kicker">
            {unit} {current.position} of {stops.length}
          </p>
          <h2>{current.title}</h2>
          {limit !== current.position && next && !next.hidden && (
            <button
              type="button"
              className="story-link"
              onClick={() => {
                onPlace({ stop: current.position, straight: place.straight });
                setLimit(current.position);
              }}
            >
              I have only got this far: hide what follows
            </button>
          )}
        </div>
        <div className="stop-controls">
          <div role="group" aria-label="Reading style" className="story-tabs">
            <button
              type="button"
              aria-pressed={!place.straight}
              onClick={() =>
                onPlace({ stop: current.position, straight: false })
              }
            >
              Stop by stop
            </button>
            <button
              type="button"
              aria-pressed={place.straight}
              onClick={() =>
                onPlace({ stop: current.position, straight: true })
              }
            >
              Read straight through
            </button>
          </div>
          <button
            type="button"
            disabled={index <= 0}
            onClick={() => choose(reached[index - 1].position)}
          >
            Previous stop
          </button>
          <button
            type="button"
            className="story-primary"
            disabled={!next}
            onClick={() => next && choose(next.position)}
          >
            {next?.hidden ? "Travel further" : "Travel on"}
          </button>
        </div>
      </div>

      <article className="arc-article">
        {cast.length > 0 && !place.straight && (
          <div className="story-cast">
            <span>In these pages</span>
            {cast.map((id) => (
              <button
                key={id}
                type="button"
                aria-expanded={panel && selected === id}
                onClick={(e) => open(id, e.currentTarget)}
              >
                {entries?.find((entry) => entry.id === id)?.displayTitle ??
                  "Entry"}
              </button>
            ))}
          </div>
        )}
        {sections.map((section) => (
          <section
            key={section.index}
            aria-labelledby={`article-heading-${section.index}`}
          >
            <h3 id={`article-heading-${section.index}`}>{section.heading}</h3>
            {section.paragraphs.map((paragraph, p) => (
              <p
                key={p}
                data-paragraph={
                  place.straight ? paragraphKey(section.index, p) : undefined
                }
              >
                {paragraph.segments.map((segment, i) =>
                  segment.nodeId ? (
                    <button
                      key={i}
                      type="button"
                      className="article-name"
                      aria-expanded={panel && selected === segment.nodeId}
                      onClick={(e) => open(segment.nodeId!, e.currentTarget)}
                    >
                      {segment.text}
                    </button>
                  ) : (
                    <Fragment key={i}>{segment.text}</Fragment>
                  ),
                )}
                {references.map((source, n) =>
                  paragraph.sourceIds.includes(source.id) ? (
                    <sup key={source.id}>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        title={source.title}
                        aria-label={`Source ${n + 1}: ${source.title}`}
                      >
                        [{n + 1}]
                      </a>
                    </sup>
                  ) : null,
                )}
              </p>
            ))}
          </section>
        ))}
        {!sections.length && (
          <p className="story-empty">
            The article does not tell this stop yet. Its moments are on the map
            above.
          </p>
        )}
        {references.length > 0 && (
          <footer>
            <h3>References</h3>
            <ol>
              {references.map((source) => (
                <li key={source.id}>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title} ↗
                  </a>
                  <small>{source.locator}</small>
                </li>
              ))}
            </ol>
            <p>{journey.spoilerScope}</p>
          </footer>
        )}
      </article>
    </div>
  );
}
