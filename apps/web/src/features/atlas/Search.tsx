"use client";
import { useId, useState } from "react";
import { useExploration } from "@/stores/ExplorationProvider";
import { NODE_IDENTITIES } from "@/features/graph/identity";
export default function Search() {
  const query = useExploration((s) => s.query),
    setQuery = useExploration((s) => s.setQuery),
    graph = useExploration((s) => s.graph),
    continuity = useExploration((s) => s.continuityId),
    types = useExploration((s) => s.types),
    select = useExploration((s) => s.selectNode);
  const [index, setIndex] = useState(0);
  const listId = useId();
  const results = (graph?.nodes ?? [])
    .filter(
      (n) =>
        (!continuity || !n.continuity_id || n.continuity_id === continuity) &&
        types.includes(n.type) &&
        `${n.title} ${n.type}`.toLowerCase().includes(query.toLowerCase()),
    )
    .slice(0, 8);
  const choose = (id: string) => {
    select(id);
    setQuery("");
  };
  return (
    <div className="atlas-search">
      <span aria-hidden="true">⌕</span>
      <input
        aria-label="Search the atlas"
        role="combobox"
        aria-expanded={Boolean(query.trim())}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          query && results[index] ? `${listId}-${results[index].id}` : undefined
        }
        placeholder="Find a character, place, or thread…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setIndex(0);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setIndex((i) => Math.max(0, Math.min(results.length - 1, i + 1)));
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setIndex((i) => Math.max(0, i - 1));
          }
          if (e.key === "Enter" && results[index]) choose(results[index].id);
          if (e.key === "Escape") setQuery("");
        }}
      />
      <kbd>/</kbd>
      {query.trim() && (
        <div
          className="search-results glass"
          id={listId}
          role="listbox"
          aria-label="Search results"
        >
          {results.map((node, i) => (
            <button
              key={node.id}
              role="option"
              id={`${listId}-${node.id}`}
              aria-selected={i === index}
              onClick={() => choose(node.id)}
            >
              <span style={{ color: NODE_IDENTITIES[node.type].color }}>
                {NODE_IDENTITIES[node.type].glyph}
              </span>
              <span>
                {node.title}
                <small>{node.type.replaceAll("_", " ")}</small>
              </span>
              <span aria-hidden="true">↗</span>
            </button>
          ))}
          {!results.length && (
            <p role="status">
              No entries found. Try another name or enable more map layers.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
