"use client";
import { useId, useState } from "react";
import type { UniverseGraph } from "@/lib/contracts";

// Rendering boundary: a future Sigma adapter can replace this component without changing the API.
export default function Atlas({ graph }: { graph: UniverseGraph }) {
  const [selectedId, setSelectedId] = useState<string | null>(
    graph.nodes[0]?.id ?? null,
  );
  const [query, setQuery] = useState("");
  const [continuity, setContinuity] = useState("all");
  const searchId = useId();
  const continuityId = useId();
  const nodes = graph.nodes.filter(
    (n) =>
      (continuity === "all" ||
        n.continuity_id === null ||
        n.continuity_id === continuity) &&
      `${n.title} ${n.type}`.toLowerCase().includes(query.toLowerCase()),
  );
  const selected = nodes.find((n) => n.id === selectedId) ?? nodes[0];
  const edges = selected
    ? graph.edges.filter(
        (e) =>
          (e.source === selected.id || e.target === selected.id) &&
          (continuity === "all" ||
            e.continuity_id === null ||
            e.continuity_id === continuity),
      )
    : [];
  const activeContinuity = graph.continuities.find(
    (c) => c.id === selected?.continuity_id,
  );
  return (
    <section className="atlas" aria-label="Interactive atlas">
      <div className="atlas-toolbar">
        <div>
          <p className="eyebrow">EXPLORE THE THREADS</p>
          <h2>A constellation of stories</h2>
        </div>
        <div className="filters">
          <label htmlFor={searchId}>
            Find an entry
            <input
              id={searchId}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Character, place, event…"
            />
          </label>
          <label htmlFor={continuityId}>
            Continuity
            <select
              id={continuityId}
              value={continuity}
              onChange={(e) => setContinuity(e.target.value)}
            >
              <option value="all">All continuities</option>
              {graph.continuities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className="atlas-grid">
        <nav className="node-list" aria-label="Atlas entries">
          <p className="eyebrow">INDEX / {nodes.length} ENTRIES</p>
          {nodes.map((n) => (
            <button
              key={n.id}
              className={selected?.id === n.id ? "node active" : "node"}
              aria-pressed={selected?.id === n.id}
              onClick={() => setSelectedId(n.id)}
            >
              <small>{n.type.replaceAll("_", " ")}</small>
              <span>{n.title}</span>
              <span aria-hidden="true">↗</span>
            </button>
          ))}
          {!nodes.length && (
            <p className="empty">No entries match this view.</p>
          )}
        </nav>
        <article className="node-detail" aria-live="polite">
          {selected ? (
            <>
              <p className="eyebrow">
                {selected.type.replaceAll("_", " ")} /{" "}
                {activeContinuity?.medium ?? "SHARED"}
              </p>
              <h2>{selected.title}</h2>
              <p className="summary">{selected.summary}</p>
              <p className="scope">
                {activeContinuity?.description ?? "Shared across continuities."}
              </p>
              {selected.metadata.illustrative === true && (
                <p className="sample">
                  ILLUSTRATIVE SAMPLE · EARLY-STORY SPOILERS
                </p>
              )}
              <div className="connections-heading">
                <h3>Connected threads</h3>
                <span>{edges.length}</span>
              </div>
              <ul className="threads">
                {edges.map((edge) => {
                  const outgoing = edge.source === selected.id;
                  const other = graph.nodes.find(
                    (n) => n.id === (outgoing ? edge.target : edge.source),
                  );
                  return (
                    <li key={edge.id}>
                      <p className="edge-label">
                        {outgoing ? "OUTGOING →" : "← INCOMING"}{" "}
                        {edge.relationship_type.replaceAll("_", " ")}
                      </p>
                      <button
                        onClick={() => {
                          setQuery("");
                          setSelectedId(other?.id ?? null);
                        }}
                      >
                        {other?.title ?? "Unknown entry"}
                        <span aria-hidden="true">↗</span>
                      </button>
                      <p>{edge.description}</p>
                    </li>
                  );
                })}
              </ul>
              {!edges.length && (
                <p>No connections charted for this entry yet.</p>
              )}
            </>
          ) : (
            <div className="notice">
              <h2>No entries to explore.</h2>
              <p>Try another search or continuity.</p>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
