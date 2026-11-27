"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { themeForUniverse, themeStyle } from "@/features/chronicle/design";
import {
  LANGUAGE_NAMES,
  STATE_LABELS,
  call,
  type Guide,
  type GuideJob,
  type GuideSource,
} from "@/features/search/model";

interface Answer {
  job: GuideJob;
  guide: Guide | null;
}

/** A page's progress while it is written, then the page with every source to hand. */
export default function GuidePage({ id }: { id: string }) {
  const [answer, setAnswer] = useState<Answer | null>(null),
    [error, setError] = useState(""),
    [shown, setShown] = useState(false),
    [round, setRound] = useState(0);
  const building = !answer || answer.job.state === "building";

  useEffect(() => {
    let live = true;
    const read = () =>
      call<Answer>(`/${id}`)
        .then((data) => {
          if (!live) return;
          setAnswer(data);
          setError("");
        })
        .catch((problem: Error) => live && setError(problem.message));
    void read();
    const timer = building ? setInterval(read, 4000) : undefined;
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [id, building, round]);

  const resume = () =>
    call<GuideJob>(`/${id}/resume`, {})
      .then((job) => {
        setAnswer({ job, guide: null });
        setRound((n) => n + 1);
      })
      .catch((problem: Error) => setError(problem.message));

  const job = answer?.job,
    guide = answer?.guide;
  return (
    <div
      className="chronicle-shell new-story guide-page"
      style={themeStyle(themeForUniverse())}
    >
      <header>
        <Link href="/">← New search</Link>
        <h1>{guide?.title ?? job?.title ?? "Opening the page"}</h1>
        {guide ? (
          <p>
            An AI draft from Wikipedia, not verified. Open a source number to
            check any paragraph.
          </p>
        ) : (
          job && <p>{job.story}</p>
        )}
      </header>
      {error && (
        <p className="new-error" role="alert">
          {error}
        </p>
      )}
      {job && !guide && (
        <section className="new-card" aria-labelledby="guide-progress">
          <h2 id="guide-progress">{STATE_LABELS[job.state]}</h2>
          {job.state === "building" && (
            <p className="new-note">
              This can take several minutes on the free models. You can leave
              this page and come back.
            </p>
          )}
          {job.error && (
            <p className="new-error" role="alert">
              {job.error}
            </p>
          )}
          {(job.state === "failed" || job.state === "interrupted") && (
            <button type="button" className="story-primary" onClick={resume}>
              Try again
            </button>
          )}
          <ul className="new-log" aria-live="polite">
            {job.messages.slice(-14).map((message, index) => (
              <li key={`${index}-${message}`}>{message}</li>
            ))}
          </ul>
        </section>
      )}
      {guide &&
        (shown ? (
          <GuideBody guide={guide} />
        ) : (
          <section className="new-card">
            <h2>Spoilers ahead</h2>
            <p>
              Wikipedia describes events from the whole story, including late
              ones, and this page may too.
            </p>
            <button
              type="button"
              className="story-primary"
              onClick={() => setShown(true)}
            >
              Show the page
            </button>
          </section>
        ))}
    </div>
  );
}

function GuideBody({ guide }: { guide: Guide }) {
  const sources = new Map(guide.sources.map((s) => [s.number, s]));
  const pages = [...new Map(guide.sources.map((s) => [s.url, s])).values()];
  const translated = guide.sources.some((s) => s.original);
  return (
    <article className="guide-body">
      {translated && (
        <p className="new-note">
          Some sources were machine translated from Japanese or Chinese. The
          original is shown beside each translation.
        </p>
      )}
      <nav aria-label="On this page" className="guide-contents">
        {guide.sections.map((s, index) => (
          <a key={s.heading} href={`#part-${index}`}>
            {s.heading}
          </a>
        ))}
        {guide.cast.length > 0 && <a href="#cast">Cast</a>}
      </nav>
      {guide.sections.map((section, index) => (
        <section key={section.heading} id={`part-${index}`}>
          <h2>{section.heading}</h2>
          {section.paragraphs.length === 0 && (
            <p className="new-note">Not found in the pages that were read.</p>
          )}
          {section.paragraphs.map((p, n) => (
            <Cited key={n} text={p.text} cites={p.cites} sources={sources} />
          ))}
        </section>
      ))}
      {(["main", "supporting"] as const).map((role) => {
        const members = guide.cast.filter((m) => m.role === role);
        if (!members.length) return null;
        return (
          <section key={role} id={role === "main" ? "cast" : undefined}>
            <h2>{role === "main" ? "Main cast" : "Supporting cast"}</h2>
            <div className="guide-cast">
              {members.map((member) => (
                <div key={member.name}>
                  <h3>{member.name}</h3>
                  <Cited
                    text={member.text}
                    cites={member.cites}
                    sources={sources}
                  />
                  <Link
                    href={{
                      pathname: "/",
                      query: {
                        character: member.name,
                        story: guide.story,
                      },
                    }}
                  >
                    More about {member.name} →
                  </Link>
                </div>
              ))}
            </div>
          </section>
        );
      })}
      <footer>
        <h2>Sources</h2>
        <ul>
          {pages.map((page) => (
            <li key={page.url}>
              <a href={page.url} rel="noreferrer" target="_blank">
                {page.title}
              </a>{" "}
              ({LANGUAGE_NAMES[page.language] ?? page.language} Wikipedia,{" "}
              <a href={page.licence} rel="noreferrer" target="_blank">
                licence
              </a>
              )
            </li>
          ))}
        </ul>
        <p className="new-note">
          Text adapted from Wikipedia contributors
          {translated ? ", with machine translation" : ""}, under its licence.
        </p>
        {guide.notes.length > 0 && (
          <details>
            <summary>{guide.notes.length} checking notes</summary>
            <ul>
              {guide.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </details>
        )}
      </footer>
    </article>
  );
}

function Cited({
  text,
  cites,
  sources,
}: {
  text: string;
  cites: number[];
  sources: Map<number, GuideSource>;
}) {
  const [open, setOpen] = useState<number | null>(null);
  const source = open === null ? undefined : sources.get(open);
  return (
    <div className="guide-paragraph">
      <p>
        {text}{" "}
        {cites.map((number) => (
          <button
            key={number}
            type="button"
            aria-expanded={open === number}
            aria-label={`Source ${number}`}
            onClick={() => setOpen(open === number ? null : number)}
          >
            {number}
          </button>
        ))}
      </p>
      {source && (
        <aside aria-label={`Source ${source.number}`}>
          <strong>
            <a href={source.url} rel="noreferrer" target="_blank">
              {source.title}
            </a>
            {source.heading && ` · ${source.heading}`}
          </strong>
          <p>{source.text}</p>
          {source.original && (
            <>
              <small>
                Original {LANGUAGE_NAMES[source.language] ?? source.language}
              </small>
              <p lang={source.language}>{source.original}</p>
            </>
          )}
        </aside>
      )}
    </div>
  );
}
