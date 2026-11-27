"use client";
import { useState } from "react";
import Link from "next/link";
import { STATE_LABELS, isRunning, type Build } from "./model";

/** One build: its progress, the page list to check, and the way into the story. */
export default function BuildProgress({
  build,
  busy,
  onConfirm,
  onResume,
}: {
  build: Build;
  busy: boolean;
  onConfirm: (pages: Build["pages"]) => void;
  onResume: () => void;
}) {
  // The reader's corrections to the proposed page list.
  const [dropped, setDropped] = useState<string[]>([]);
  const [moved, setMoved] = useState<Record<string, number>>({});
  const kept = build.pages
    .filter((p) => !dropped.includes(p.title))
    .map((p) => ({ ...p, position: moved[p.title] ?? p.position }));
  return (
    <section className="new-card" aria-live="polite">
      <p className="story-kicker">
        {build.story} · {build.title}
      </p>
      <h2>{STATE_LABELS[build.state]}</h2>
      {isRunning(build) && (
        <p className="new-note">
          This runs on free model allowances and can take many minutes. You can
          leave this page and come back.
        </p>
      )}
      {build.state === "choose_pages" && (
        <>
          <p className="new-note">
            These pages were chosen to tell the arc, in this order. Untick any
            that do not belong and correct the order numbers.
          </p>
          <ol className="new-pages">
            {build.pages.map((page) => (
              <li key={page.title}>
                <label>
                  <input
                    type="checkbox"
                    checked={!dropped.includes(page.title)}
                    onChange={(e) =>
                      setDropped(
                        e.target.checked
                          ? dropped.filter((t) => t !== page.title)
                          : [...dropped, page.title],
                      )
                    }
                  />
                  <span>{page.title}</span>
                </label>
                <input
                  type="number"
                  min={1}
                  max={100000}
                  aria-label={`Order of ${page.title}`}
                  value={moved[page.title] ?? page.position}
                  onChange={(e) =>
                    setMoved({
                      ...moved,
                      [page.title]: Math.max(1, Number(e.target.value) || 1),
                    })
                  }
                />
              </li>
            ))}
          </ol>
          <button
            type="button"
            className="story-primary"
            disabled={busy || kept.length < 3}
            onClick={() => onConfirm(kept)}
          >
            Build the story from {kept.length} pages
          </button>
          {kept.length < 3 && (
            <p className="new-note">Keep at least three pages.</p>
          )}
        </>
      )}
      {build.state === "ready" && (
        <>
          <p className="new-note">
            The draft is not verified. Read it against its sources.
          </p>
          <Link className="story-primary" href={`/universes/${build.slug}`}>
            Open the story
          </Link>
        </>
      )}
      {(build.state === "failed" || build.state === "interrupted") && (
        <>
          <p role="alert">
            {build.error || "The application stopped while this was running."}
          </p>
          <button
            type="button"
            className="story-primary"
            disabled={busy}
            onClick={onResume}
          >
            Resume
          </button>
        </>
      )}
      {build.messages.length > 0 && (
        <details open={isRunning(build)}>
          <summary>Progress notes</summary>
          <ul className="new-log">
            {build.messages.slice(-12).map((message, i) => (
              <li key={`${i}-${message}`}>{message}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
