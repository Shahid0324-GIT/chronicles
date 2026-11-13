"use client";
import { useExploration } from "@/stores/ExplorationProvider";

export default function ReaderControls() {
  const boundary = useExploration((s) => s.spoilerPosition),
    setBoundary = useExploration((s) => s.setSpoilerPosition),
    entries = useExploration((s) => s.narrative.entryIndex),
    inspect = useExploration((s) => s.selectNode);
  return (
    <div className="story-scope-controls">
      <label>
        Spoilers through episode{" "}
        <input
          aria-label="Spoilers through episode"
          type="number"
          min={1}
          max={100000}
          placeholder="All"
          value={boundary ?? ""}
          onChange={(e) =>
            setBoundary(e.target.value ? Number(e.target.value) : null)
          }
        />
      </label>
      {!!entries?.length && (
        <label>
          Encyclopedia{" "}
          <select
            aria-label="Open encyclopedia entry"
            value=""
            onChange={(e) => {
              if (e.target.value) inspect(e.target.value, "inspection");
            }}
          >
            <option value="">Choose an entry…</option>
            {entries.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.displayTitle}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
