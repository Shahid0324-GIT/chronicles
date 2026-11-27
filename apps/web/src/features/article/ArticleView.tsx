"use client";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import type { NarrativeJourney } from "@/features/narrative/contracts";
import { DRAFT_NOTE, isDraftWorld } from "@/features/narrative/draft";
import TimelineRail from "./TimelineRail";
import {
  eventsAt,
  eventTargets,
  paragraphKey,
  readingIndex,
  readingMinutes,
} from "./model";

/** The arc told as one long article; names open their page without losing the place. */
export default function ArticleView({
  journey,
}: {
  journey: NarrativeJourney;
}) {
  const story = journey.story ?? [],
    sources = useExploration((s) => s.narrative.sources),
    inspect = useExploration((s) => s.selectNode),
    selectMilestone = useExploration((s) => s.selectMilestone),
    selected = useExploration((s) => s.selectedId),
    panel = useExploration((s) => s.mode === "explore" && !!s.selectedId),
    draft = useExploration((s) => isDraftWorld(s.graph?.universe.slug)),
    position = useExploration((s) => s.journeyIndex);
  const root = useRef<HTMLDivElement>(null);
  const opened = useRef<HTMLButtonElement | null>(null);
  const [reading, setReading] = useState(paragraphKey(0, 0));
  const told = eventTargets(story);
  const cited = new Set(
    story.flatMap((s) => s.paragraphs.flatMap((p) => p.sourceIds)),
  );
  const references = sources.filter((s) => cited.has(s.id));

  const goTo = useCallback((anchor: string, smooth = true) => {
    const target = root.current?.querySelector<HTMLElement>(
        `[data-anchor="${anchor}"]`,
      ),
      scroller = root.current?.closest<HTMLElement>(".chronicle-canvas");
    if (!target || !scroller) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.focus({ preventScroll: true });
    scroller.scrollTo({
      top:
        scroller.scrollTop +
        target.getBoundingClientRect().top -
        scroller.getBoundingClientRect().top -
        24,
      behavior: smooth && !still ? "smooth" : "auto",
    });
  }, []);

  useEffect(() => {
    const scroller = root.current?.closest<HTMLElement>(".chronicle-canvas");
    if (!scroller) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      const paragraphs = [
        ...(root.current?.querySelectorAll<HTMLElement>("[data-paragraph]") ??
          []),
      ];
      const at = readingIndex(
        paragraphs.map((p) => p.getBoundingClientRect().top),
        scroller.getBoundingClientRect().top + scroller.clientHeight * 0.35,
        scroller.scrollTop > 0 &&
          scroller.scrollTop + scroller.clientHeight >=
            scroller.scrollHeight - 2,
      );
      const key = paragraphs[at]?.dataset.paragraph;
      if (key) setReading(key);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    schedule();
    scroller.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(frame);
      scroller.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [journey]);

  // Arriving from the story map keeps the reader's moment.
  const arrival = useRef(
    position > 0 ? told.get(journey.steps[position]?.eventNodeId ?? "") : null,
  );
  useEffect(() => {
    if (arrival.current) goTo(arrival.current, false);
  }, [goTo]);

  // Closing a page returns the keyboard to the name that opened it.
  useEffect(() => {
    if (!selected && opened.current) {
      opened.current.focus({ preventScroll: true });
      opened.current = null;
    }
  }, [selected]);

  const section = Number(reading.split("-")[0]);
  return (
    <div ref={root} className="article-view" data-panel={panel}>
      <nav className="article-contents" aria-label="Article contents">
        <h2>Contents</h2>
        <ol>
          {story.map((part, s) => (
            <li key={s}>
              <button
                type="button"
                aria-current={s === section ? "location" : undefined}
                onClick={() => goTo(`section-${s}`)}
              >
                {part.heading}
              </button>
            </li>
          ))}
          {references.length > 0 && (
            <li>
              <button type="button" onClick={() => goTo("references")}>
                References
              </button>
            </li>
          )}
        </ol>
      </nav>
      <article className="arc-article">
        <header>
          <p className="folio-eyebrow">
            {draft ? "AI DRAFT ARTICLE" : "ARC ARTICLE"} ·{" "}
            {readingMinutes(story)} MIN READ
          </p>
          <h1>{journey.title}</h1>
          {draft && <p className="article-note">{DRAFT_NOTE}</p>}
          <p className="article-lead">
            {journey.overview ?? journey.introduction}
          </p>
        </header>
        {story.map((part, s) => (
          <section key={s} aria-labelledby={`article-heading-${s}`}>
            <h2
              id={`article-heading-${s}`}
              data-anchor={`section-${s}`}
              tabIndex={-1}
            >
              {part.heading}
            </h2>
            {part.paragraphs.map((paragraph, p) => (
              <p
                key={p}
                data-paragraph={paragraphKey(s, p)}
                data-anchor={paragraphKey(s, p)}
                tabIndex={-1}
              >
                {paragraph.segments.map((segment, i) =>
                  segment.nodeId ? (
                    <button
                      key={i}
                      type="button"
                      className="article-name"
                      aria-expanded={panel && selected === segment.nodeId}
                      onClick={(e) => {
                        opened.current = e.currentTarget;
                        inspect(segment.nodeId!, "inspection");
                      }}
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
        {references.length > 0 && (
          <footer>
            <h2 data-anchor="references" tabIndex={-1}>
              References
            </h2>
            <ol>
              {references.map((source) => (
                <li key={source.id}>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title} ↗
                  </a>
                </li>
              ))}
            </ol>
            <p>{journey.spoilerScope}</p>
          </footer>
        )}
      </article>
      <TimelineRail
        journey={journey}
        current={eventsAt(story, reading)}
        told={told}
        onSelect={(index) => {
          const step = journey.steps[index];
          selectMilestone(index);
          const anchor = told.get(step.eventNodeId);
          if (anchor) goTo(anchor);
          else inspect(step.eventNodeId, "inspection");
        }}
      />
    </div>
  );
}
