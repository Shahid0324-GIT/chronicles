"use client";
import { useEffect, useRef } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { useAtlasMotion, useExitMotion } from "@/animations/useAtlasMotion";
import { NODE_IDENTITIES, humanize } from "@/features/graph/identity";
import LoreEntryLinks from "@/features/narrative/LoreEntryLinks";
import IconButton from "@/components/ui/IconButton";
import MediaArtwork from "./MediaArtwork";
import { resolveMedia } from "./media-registry";
import { useEncyclopediaEntry } from "@/features/narrative/encyclopedia";
export default function ContextPanel() {
  const mode = useExploration((s) => s.mode);
  const graph = useExploration((s) => s.graph),
    selectedId = useExploration((s) => s.selectedId),
    selectedEdgeId = useExploration((s) => s.selectedEdgeId),
    minimized = useExploration((s) => s.panelMinimized),
    minimize = useExploration((s) => s.minimizePanel),
    clear = useExploration((s) => s.clearSelection),
    select = useExploration((s) => s.selectNode),
    continuity = useExploration((s) => s.continuityId),
    types = useExploration((s) => s.types);
  const catalog = useExploration((s) => s.narrative),
    boundary = useExploration((s) => s.spoilerPosition);
  const generated =
    catalog.availability?.kind === "generated" || boundary !== null;
  const result = useEncyclopediaEntry(
    selectedId,
    graph?.universe.slug,
    continuity,
    boundary,
    generated,
    catalog.availability?.revision,
  );
  const entry = result?.entry;
  const root = useRef<HTMLElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useAtlasMotion(root, `${mode}-${selectedId}-${minimized}`, "card");
  const dismiss = useExitMotion(
    root,
    () => {
      clear();
      document
        .querySelector<HTMLElement>(
          '[aria-label="Interactive universe map"], [aria-label="Narrative atlas"]',
        )
        ?.focus({ preventScroll: true });
    },
    selectedId,
  );
  useEffect(() => {
    if (selectedId && !minimized)
      heading.current?.focus({ preventScroll: true });
  }, [selectedId, minimized, mode]);
  const node = graph?.nodes.find((n) => n.id === selectedId);
  if (!node || !graph || mode !== "explore") return null;
  const visual = NODE_IDENTITIES[node.type];
  const edges = graph.edges.filter(
    (e) =>
      (e.source === node.id || e.target === node.id) &&
      (!generated ||
        entry?.connections.some((connection) => connection.id === e.id)) &&
      (!continuity || !e.continuity_id || e.continuity_id === continuity),
  );
  const asset = resolveMedia(node.id, node.type);
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId);
  return (
    <aside
      ref={root}
      className={`context-panel glass ${minimized ? "minimized" : ""}`}
      aria-label="Story information"
    >
      <div className="panel-actions">
        <span className="eyebrow" style={{ color: visual.color }}>
          {visual.glyph} {node.type.replaceAll("_", " ")}
        </span>
        <div>
          <IconButton
            label={
              minimized
                ? "Expand story information"
                : "Minimize story information"
            }
            onClick={minimize}
          >
            {minimized ? "＋" : "−"}
          </IconButton>
          <IconButton label="Close story information" onClick={dismiss}>
            ×
          </IconButton>
        </div>
      </div>
      {!minimized && <MediaArtwork asset={asset} className="context-art" />}
      <div className="context-copy">
        <h2 ref={heading} tabIndex={-1}>
          {generated
            ? (entry?.display_title ?? "Opening encyclopedia entry…")
            : node.title}
        </h2>
        {!minimized && (
          <>
            <p className="node-summary">
              {generated
                ? (entry?.short_introduction ??
                  result?.error ??
                  "Loading the source-backed entry…")
                : node.summary}
            </p>
            {generated &&
              entry?.sections.map((section) => (
                <section key={section.name}>
                  <h3>{humanize(section.name)}</h3>
                  {section.statements.map((statement, index) => (
                    <p key={index}>{statement.text}</p>
                  ))}
                </section>
              ))}
            {generated && !!entry?.aliases.length && (
              <details>
                <summary>Names in the sources</summary>
                <p>{entry.aliases.join(" · ")}</p>
              </details>
            )}
            {generated && !!entry?.source_references.length && (
              <details>
                <summary>
                  Sources &amp; evidence ({entry.source_references.length})
                </summary>
                {entry.source_references.map((source, index) => (
                  <div key={`${source.id}-${index}`}>
                    <a href={source.url} target="_blank" rel="noreferrer">
                      {source.title} ↗
                    </a>
                    <small>{source.locator}</small>
                    {source.quote && <blockquote>{source.quote}</blockquote>}
                  </div>
                ))}
              </details>
            )}
            {selectedEdge && (
              <div className="selected-relationship">
                <p className="eyebrow">
                  {humanize(selectedEdge.relationship_type)}
                </p>
                {!generated && <p>{selectedEdge.description}</p>}
              </div>
            )}
            <div className="node-provenance">
              <span>
                {graph.continuities.find((c) => c.id === node.continuity_id)
                  ?.name ?? "Shared knowledge"}
              </span>
              {node.metadata.illustrative === true && (
                <small>Illustrative sample · early-story spoilers</small>
              )}
            </div>
            <LoreEntryLinks nodeId={node.id} />
            <div className="thread-title">
              <h3>Follow a thread</h3>
              <span>{edges.length}</span>
            </div>
            <ul className="context-threads">
              {edges.map((edge) => {
                const outgoing = edge.source === node.id;
                const other = graph.nodes.find(
                  (n) => n.id === (outgoing ? edge.target : edge.source),
                );
                if (!other) return null;
                const visible = types.includes(other.type);
                return (
                  <li key={edge.id}>
                    <span>
                      {outgoing ? "→" : "←"} {humanize(edge.relationship_type)}
                    </span>
                    <button
                      disabled={!visible}
                      title={
                        generated
                          ? humanize(edge.relationship_type)
                          : edge.description
                      }
                      onClick={() => select(other.id)}
                    >
                      {generated
                        ? (catalog.entryIndex?.find(
                            (item) => item.id === other.id,
                          )?.displayTitle ?? "Related entry")
                        : other.title}
                      <span aria-hidden="true">↗</span>
                    </button>
                    {!visible && (
                      <small>
                        Enable {NODE_IDENTITIES[other.type].label.toLowerCase()}{" "}
                        to follow
                      </small>
                    )}
                  </li>
                );
              })}
            </ul>
            {!edges.length && (
              <p className="muted">
                No connections have been charted for this entry.
              </p>
            )}
            <p className="art-credit">{asset.credit}</p>
          </>
        )}
      </div>
    </aside>
  );
}
