"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { themeForUniverse, themeStyle } from "@/features/chronicle/design";
import BuildProgress from "./BuildProgress";
import {
  MEDIUMS,
  STATE_LABELS,
  call,
  isRunning,
  type Build,
  type SiteIdea,
  type SiteReport,
} from "./model";

/** Name a story and an arc, approve a source, check the pages, then read it. */
export default function NewStory() {
  const [story, setStory] = useState(""),
    [arc, setArc] = useState(""),
    [about, setAbout] = useState(""),
    [medium, setMedium] = useState<(typeof MEDIUMS)[number]>("game"),
    [url, setUrl] = useState(""),
    [ideas, setIdeas] = useState<SiteIdea[] | null>(null),
    [report, setReport] = useState<SiteReport | null>(null),
    [headings, setHeadings] = useState<string[]>([]),
    [terms, setTerms] = useState(false),
    [cloud, setCloud] = useState(false),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [builds, setBuilds] = useState<Build[]>([]),
    [open, setOpen] = useState<string | null>(null);
  const named = story.trim().length > 1 && arc.trim().length > 1;
  const current = builds.find((b) => `${b.world}/${b.arc}` === open);

  const keep = (build: Build) =>
    setBuilds((list) => [
      build,
      ...list.filter((b) => b.world !== build.world || b.arc !== build.arc),
    ]);

  /** Runs one request, showing what it is doing and why it failed. */
  const run = useCallback(async (label: string, work: () => Promise<void>) => {
    setBusy(label);
    setError("");
    try {
      await work();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Request failed.");
    } finally {
      setBusy("");
    }
  }, []);

  useEffect(() => {
    let live = true;
    call<{ jobs: Build[] }>("")
      .then((data) => live && setBuilds(data.jobs))
      .catch((problem: Error) => live && setError(problem.message));
    return () => {
      live = false;
    };
  }, []);

  const watching = current && isRunning(current) ? open : null;
  useEffect(() => {
    if (!watching) return;
    const timer = setInterval(() => {
      call<Build>(`/${watching}`)
        .then(keep)
        .catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [watching]);

  const check = (event: FormEvent) => {
    event.preventDefault();
    setReport(null);
    setHeadings([]);
    setTerms(false);
    void run("Checking the site", async () => {
      setReport(await call<SiteReport>("/sites/check", { url: url.trim() }));
    });
  };

  const start = () =>
    void run("Starting", async () => {
      const build = await call<Build>("", {
        story: story.trim(),
        arc: arc.trim(),
        about: about.trim(),
        medium,
        site_url: url.trim(),
        sections: headings,
        terms_confirmed: terms,
        cloud_allowed: cloud,
      });
      keep(build);
      setOpen(`${build.world}/${build.arc}`);
    });

  return (
    <div
      className="chronicle-shell new-story"
      style={themeStyle(themeForUniverse())}
    >
      <header>
        <Link href="/">← Back to the atlas</Link>
        <h1>Chart a new story</h1>
        <p>
          Name one arc, choose where to read it, and check what was found. The
          result is a draft for you to review.
        </p>
      </header>
      {error && (
        <p className="new-error" role="alert">
          {error}
        </p>
      )}
      {builds.length > 0 && (
        <nav className="new-builds" aria-label="Your builds">
          {builds.map((b) => (
            <button
              key={`${b.world}/${b.arc}`}
              type="button"
              aria-pressed={open === `${b.world}/${b.arc}`}
              onClick={() => setOpen(`${b.world}/${b.arc}`)}
            >
              <strong>
                {b.story} · {b.title}
              </strong>
              <small>{STATE_LABELS[b.state]}</small>
            </button>
          ))}
          {current && (
            <button type="button" onClick={() => setOpen(null)}>
              <strong>+ Another story</strong>
            </button>
          )}
        </nav>
      )}
      {current ? (
        <BuildProgress
          key={`${current.world}/${current.arc}/${current.state}`}
          build={current}
          busy={!!busy}
          onConfirm={(pages) =>
            void run("Starting the build", async () => {
              keep(await call<Build>(`/${open}/pages`, { pages }));
            })
          }
          onResume={() =>
            void run("Resuming", async () => {
              keep(await call<Build>(`/${open}/resume`, {}));
            })
          }
        />
      ) : (
        <>
          <section className="new-card" aria-labelledby="new-step-story">
            <h2 id="new-step-story">1 · The story</h2>
            <div className="new-fields">
              <label>
                Story
                <input
                  value={story}
                  maxLength={180}
                  placeholder="Kingdom Hearts"
                  onChange={(e) => setStory(e.target.value)}
                />
              </label>
              <label>
                Arc
                <input
                  value={arc}
                  maxLength={100}
                  placeholder="Chain of Memories"
                  onChange={(e) => setArc(e.target.value)}
                />
              </label>
              <label>
                Kind
                <select
                  value={medium}
                  onChange={(e) => setMedium(e.target.value as typeof medium)}
                >
                  {MEDIUMS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="wide">
                What should it cover? (optional)
                <input
                  value={about}
                  maxLength={400}
                  placeholder="Chapters 1 to 8, or each world in order"
                  onChange={(e) => setAbout(e.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="new-card" aria-labelledby="new-step-source">
            <h2 id="new-step-source">2 · Where to read it</h2>
            <p className="new-note">
              Paste the link to the wiki page about this story or arc.
            </p>
            <button
              type="button"
              disabled={!named || !!busy}
              onClick={() =>
                void run("Asking for ideas", async () => {
                  const found = await call<{ sites: SiteIdea[] }>(
                    "/sites/suggest",
                    { story: story.trim(), arc: arc.trim(), about },
                  );
                  setIdeas(found.sites);
                })
              }
            >
              Suggest wikis
            </button>
            {ideas && (
              <>
                <p className="new-note">
                  {ideas.length
                    ? "These are AI guesses. Nothing has been checked, and a link may not exist."
                    : "No ideas came back. Paste a link you know."}
                </p>
                <ul className="new-ideas">
                  {ideas.map((idea) => (
                    <li key={idea.url}>
                      <button type="button" onClick={() => setUrl(idea.url)}>
                        Use
                      </button>
                      <span>
                        <strong>{idea.name}</strong> {idea.why}
                        <small>{idea.url}</small>
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <form className="new-check" onSubmit={check}>
              <label>
                Page link
                <input
                  type="url"
                  required
                  value={url}
                  placeholder="https://wiki.example.org/wiki/Your_arc"
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setReport(null);
                  }}
                />
              </label>
              <button type="submit" disabled={!url || !!busy}>
                Check this site
              </button>
            </form>
            {report && !report.allowed && (
              <p className="new-error" role="alert">
                {report.reason}
              </p>
            )}
          </section>

          {report?.allowed && (
            <section className="new-card" aria-labelledby="new-step-approve">
              <h2 id="new-step-approve">3 · Approve and start</h2>
              <p>
                <strong>{report.name}</strong> allows the app to read “
                {report.page}”.
              </p>
              <p className="new-note">Stated licence: {report.licence}</p>
              {report.headings.length > 0 && (
                <details>
                  <summary>
                    This page tells several stories? Choose its story headings
                  </summary>
                  <div className="new-headings">
                    {report.headings.slice(0, 10 * 6).map((heading) => (
                      <label key={heading}>
                        <input
                          type="checkbox"
                          checked={headings.includes(heading)}
                          disabled={
                            !headings.includes(heading) && headings.length >= 10
                          }
                          onChange={(e) =>
                            setHeadings(
                              e.target.checked
                                ? [...headings, heading]
                                : headings.filter((h) => h !== heading),
                            )
                          }
                        />
                        {heading}
                      </label>
                    ))}
                  </div>
                </details>
              )}
              <label className="new-consent">
                <input
                  type="checkbox"
                  checked={terms}
                  onChange={(e) => setTerms(e.target.checked)}
                />
                I have checked that this site’s terms allow automated reading.
              </label>
              <label className="new-consent">
                <input
                  type="checkbox"
                  checked={cloud}
                  onChange={(e) => setCloud(e.target.checked)}
                />
                Send its text to the free cloud models (Groq and Gemini).
                Gemini’s free tier may use it to improve Google’s products.
              </label>
              {!cloud && (
                <p className="new-note">
                  Without this, only the model on your computer is used, which
                  is very slow.
                </p>
              )}
              <button
                type="button"
                className="story-primary"
                disabled={!named || !terms || !!busy}
                onClick={start}
              >
                Find the arc’s pages
              </button>
              {!named && (
                <p className="new-note">Name the story and arc above first.</p>
              )}
            </section>
          )}
        </>
      )}
      {busy && (
        <p className="new-busy" role="status">
          {busy}…
        </p>
      )}
    </div>
  );
}
