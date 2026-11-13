"use client";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  readResearchJob,
  saveResearchJob,
  subscribeResearchJobs,
} from "./session";
import { useExploration } from "@/stores/ExplorationProvider";
import {
  getResearchSummary,
  startResearch,
  terminal,
  type ResearchSummary,
} from "./client";

export default function ResearchControls() {
  const universe = useExploration((s) => s.activeUniverse),
    continuity = useExploration((s) => s.continuityId),
    continuities = useExploration((s) => s.graph?.continuities),
    availability = useExploration((s) => s.narrative.availability),
    refresh = useExploration((s) => s.refreshAtlas);
  return (
    <div className="research-entry">
      <span
        className="research-availability"
        title={availability?.reason}
        role="status"
      >
        {availability?.kind === "generated"
          ? "Research archive"
          : "Curated fallback"}
      </span>
      <ResearchPanel
        key={`${universe?.id}:${continuity}`}
        universe={universe}
        continuity={continuity}
        continuityName={continuities?.find((c) => c.id === continuity)?.name}
        refresh={refresh}
      />
    </div>
  );
}
function ResearchPanel({
  universe,
  continuity,
  continuityName,
  refresh,
}: {
  universe: { id: string; title: string } | null;
  continuity: string | null;
  continuityName?: string;
  refresh: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false),
    [objective, setObjective] = useState(""),
    [position, setPosition] = useState(""),
    [focus, setFocus] = useState<"story" | "encyclopedia">("story"),
    [jobOverride, setJobOverride] = useState<string | null>(null),
    [summary, setSummary] = useState<ResearchSummary | null>(null),
    [error, setError] = useState<string | null>(null),
    [busy, setBusy] = useState(false),
    [check, setCheck] = useState(0);
  const button = useRef<HTMLButtonElement>(null);
  const scope = `${universe?.id}:${continuity}`;
  const restoredJob = useSyncExternalStore(
    subscribeResearchJobs,
    () => readResearchJob(scope),
    () => null,
  );
  const job = jobOverride ?? restoredJob;
  const setJob = (id: string) => {
    setJobOverride(id);
    saveResearchJob(scope, id);
  };
  useEffect(() => {
    if (!job) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined,
      polls = 0,
      failures = 0;
    const poll = async () => {
      try {
        const next = await getResearchSummary(
          job,
          AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        );
        if (controller.signal.aborted) return;
        setSummary(next);
        setError(null);
        failures = 0;
        if (terminal(next.status)) return;
      } catch (e) {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : "Status unavailable.");
        if (++failures >= 4) return;
      }
      if (++polls >= 300) {
        setError(
          "Status polling paused. Check again to continue following this job.",
        );
        return;
      }
      timer = setTimeout(() => void poll(), 3000);
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [job, check]);
  const close = () => {
    setOpen(false);
    button.current?.focus();
  };
  return (
    <>
      <button
        ref={button}
        aria-expanded={open}
        aria-controls="research-panel"
        onClick={() => setOpen(!open)}
      >
        Research
      </button>
      {open && (
        <section
          id="research-panel"
          className="research-panel"
          aria-label="Research this universe"
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.stopPropagation();
              close();
            }
          }}
        >
          <header>
            <strong>Research this universe</strong>
            <button aria-label="Close research" onClick={close}>
              ×
            </button>
          </header>
          <p>
            {universe?.title} ·{" "}
            {continuityName ?? "Choose one continuity above"}
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!universe || !continuity || busy) return;
              setBusy(true);
              setError(null);
              try {
                setJob(
                  await startResearch(
                    universe.id,
                    continuity,
                    objective.trim(),
                    position ? Number(position) : undefined,
                    focus,
                  ),
                );
                setSummary(null);
              } catch (e) {
                setError(
                  e instanceof Error ? e.message : "Could not start research.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Focused objective
              <textarea
                aria-label="Research objective"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                required
                minLength={20}
                maxLength={1500}
                rows={3}
              />
            </label>
            <label>
              Research focus{" "}
              <select
                aria-label="Research focus"
                value={focus}
                onChange={(e) =>
                  setFocus(
                    e.target.value === "encyclopedia"
                      ? "encyclopedia"
                      : "story",
                  )
                }
              >
                <option value="story">Story moments</option>
                <option value="encyclopedia">Encyclopedia topic</option>
              </select>
            </label>
            <label>
              Through episode source (optional)
              <input
                aria-label="Research episode boundary"
                type="number"
                min="1"
                max="100000"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={
                !continuity ||
                busy ||
                (!!job && (!summary || !terminal(summary.status)))
              }
            >
              {" "}
              {busy ? "Queuing…" : "Start research"}
            </button>
          </form>
          {job && (
            <div
              className="research-summary"
              aria-live="polite"
              data-job-id={job}
            >
              <p>
                <strong>{summary?.status ?? "queued"}</strong> ·{" "}
                {summary?.stage.replaceAll("_", " ") ??
                  "Waiting for the local worker"}
              </p>
              {summary && (
                <>
                  <p>
                    {summary.model_calls} model calls · {summary.cache_hits}{" "}
                    reused responses · {summary.sources} sources
                  </p>
                  <p>
                    {summary.accepted_relationships} accepted links ·{" "}
                    {summary.unresolved_findings} unresolved findings
                  </p>
                  <ul>
                    {summary.discoveries.slice(0, 5).map((d) => (
                      <li key={d.id}>{d.label}</li>
                    ))}
                  </ul>
                  {summary.error && <p>{summary.error.replaceAll("_", " ")}</p>}
                </>
              )}
              <button onClick={() => setCheck((v) => v + 1)}>
                Check status
              </button>
            </div>
          )}
          {error && <p role="alert">{error}</p>}
          <button
            onClick={async () => {
              setBusy(true);
              try {
                await refresh();
                setError(null);
              } catch (e) {
                setError(
                  e instanceof Error ? e.message : "Refresh unavailable.",
                );
              } finally {
                setBusy(false);
              }
            }}
            disabled={busy}
          >
            Refresh story atlas
          </button>
          <small>
            Uses permitted sources in the local registry. Uncertain findings
            stay outside the story map.
          </small>
        </section>
      )}
    </>
  );
}
