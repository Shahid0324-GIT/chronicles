"use client";
import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { themeForUniverse, themeStyle } from "@/features/chronicle/design";
import {
  KIND_LABELS,
  STATE_LABELS,
  SUBJECT_LABELS,
  call,
  canBuild,
  isWikipediaPage,
  type GuideJob,
  type Intent,
  type Kind,
} from "./model";

/** Type what you want to know, check how it was read, then have it written. */
export default function SearchHome({ initial }: { initial?: Intent }) {
  const router = useRouter();
  const [query, setQuery] = useState(""),
    [intent, setIntent] = useState<Intent | null>(initial ?? null),
    [link, setLink] = useState(""),
    [approved, setApproved] = useState(false),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [saved, setSaved] = useState<GuideJob[]>([]);

  useEffect(() => {
    let live = true;
    call<{ jobs: GuideJob[] }>("")
      .then((data) => live && setSaved(data.jobs))
      .catch((problem: Error) => live && setError(problem.message));
    return () => {
      live = false;
    };
  }, []);

  const change = (part: Partial<Intent>) =>
    setIntent((now) => (now ? { ...now, ...part } : now));

  const search = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("Working out what you mean");
    setError("");
    setIntent(null);
    try {
      setIntent(await call<Intent>("/understand", { query: query.trim() }));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Search failed.");
      // The reader can still say what they want by hand.
      setIntent({
        kind: "unclear",
        story: query.trim(),
        subject: "",
        wikipedia_title: "",
      });
    } finally {
      setBusy("");
    }
  };

  const create = async () => {
    if (!intent) return;
    setBusy("Starting");
    setError("");
    try {
      const job = await call<GuideJob>("", {
        kind: intent.kind,
        story: intent.story.trim(),
        subject: intent.kind === "summary" ? "" : intent.subject.trim(),
        wikipedia_title: intent.wikipedia_title,
        link: link.trim(),
        approved,
      });
      router.push(`/guide/${job.key}`);
    } catch (problem) {
      setError(
        problem instanceof Error ? problem.message : "Could not start it.",
      );
      setBusy("");
    }
  };

  const kind =
    intent && intent.kind !== "story" && intent.kind !== "unclear"
      ? intent.kind
      : null;

  return (
    <div
      className="chronicle-shell new-story search-home"
      style={themeStyle(themeForUniverse())}
    >
      <header>
        <h1>What do you want to know?</h1>
        <p>
          Ask for a story’s summary, one of its arcs, or one of its characters.
        </p>
      </header>
      <form className="new-check search-box" onSubmit={search} role="search">
        <label>
          Search
          <input
            type="search"
            required
            minLength={2}
            maxLength={300}
            value={query}
            placeholder="Try “who is Rem in Re:Zero”"
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button type="submit" className="story-primary" disabled={!!busy}>
          Search
        </button>
      </form>
      <p className="new-note">
        Your search words are sent to a free cloud model to work out what you
        mean.
      </p>
      {error && (
        <p className="new-error" role="alert">
          {error}
        </p>
      )}
      {busy && (
        <p className="new-busy" role="status">
          {busy}…
        </p>
      )}

      {intent && (
        <section className="new-card" aria-labelledby="read-as">
          <h2 id="read-as">
            {intent.kind === "story"
              ? "A whole story is too much for one page"
              : intent.kind === "unclear"
                ? "Say what you are looking for"
                : "Here is how I read that"}
          </h2>
          {intent.kind === "story" && (
            <p>
              Telling all of {intent.story || "a story"} in full is not possible
              here. Choose a summary with its cast, one arc, or one character.
            </p>
          )}
          <div className="search-kinds" role="group" aria-label="What to write">
            {(Object.keys(KIND_LABELS) as Kind[]).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={intent.kind === option}
                onClick={() => change({ kind: option })}
              >
                {KIND_LABELS[option]}
              </button>
            ))}
          </div>
          {kind && (
            <>
              <div className="new-fields">
                <label>
                  Story
                  <input
                    value={intent.story}
                    maxLength={180}
                    onChange={(e) =>
                      change({ story: e.target.value, wikipedia_title: "" })
                    }
                  />
                </label>
                {kind !== "summary" && (
                  <label>
                    {SUBJECT_LABELS[kind]}
                    <input
                      value={intent.subject}
                      maxLength={120}
                      onChange={(e) => change({ subject: e.target.value })}
                    />
                  </label>
                )}
              </div>
              <details>
                <summary>The wrong story, or not found?</summary>
                <label>
                  Link to its Wikipedia page
                  <input
                    type="url"
                    value={link}
                    placeholder="https://en.wikipedia.org/wiki/…"
                    onChange={(e) => setLink(e.target.value)}
                  />
                </label>
                {!isWikipediaPage(link.trim()) && (
                  <p className="new-note">
                    Use an English, Japanese or Chinese Wikipedia page.
                  </p>
                )}
              </details>
              <label className="new-consent">
                <input
                  type="checkbox"
                  checked={approved}
                  onChange={(e) => setApproved(e.target.checked)}
                />
                Read Wikipedia in English, Japanese and Chinese (CC BY-SA), and
                send that text to the free cloud models (Groq and Gemini).
                Gemini’s free tier may use it to improve Google’s products.
              </label>
              <button
                type="button"
                className="story-primary"
                disabled={
                  !approved ||
                  !!busy ||
                  !canBuild(intent) ||
                  !isWikipediaPage(link.trim())
                }
                onClick={() => void create()}
              >
                Write this page
              </button>
            </>
          )}
        </section>
      )}

      {saved.length > 0 && (
        <section className="search-saved" aria-labelledby="saved-pages">
          <h2 id="saved-pages">Your pages</h2>
          <ul>
            {saved.map((job) => (
              <li key={job.key}>
                <Link href={`/guide/${job.key}`}>
                  <strong>{job.title}</strong>
                  <span>{job.story}</span>
                  <small>{STATE_LABELS[job.state]}</small>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      <nav className="search-more" aria-label="Other tools">
        <Link href="/new">Build an arc from a fan wiki</Link>
        <Link href="/atlas">Open the story atlas</Link>
      </nav>
    </div>
  );
}
