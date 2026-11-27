"use client";
import { useState } from "react";
import { useExploration } from "@/stores/ExplorationProvider";

export function usePositionUnit() {
  const medium = useExploration((s) =>
    s.graph?.continuities
      .find((c) => c.id === s.continuityId)
      ?.medium.toUpperCase(),
  );
  return medium === "MANGA" || medium === "NOVEL"
    ? "chapter"
    : medium === "ANIME"
      ? "episode"
      : "source position";
}

/** Applied on request, because changing the boundary reloads the story. */
export default function SpoilerControl() {
  const boundary = useExploration((s) => s.spoilerPosition),
    setBoundary = useExploration((s) => s.setSpoilerPosition),
    unit = usePositionUnit();
  const [value, setValue] = useState(boundary?.toString() ?? "");
  return (
    <form
      className="spoiler-form"
      onSubmit={(e) => {
        e.preventDefault();
        setBoundary(value ? Number(value) : null);
      }}
    >
      <label>
        Spoilers through {unit}
        <input
          type="number"
          min={1}
          max={100000}
          placeholder="All"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </label>
      <button type="submit">Apply</button>
      {boundary !== null && (
        <button type="button" onClick={() => setBoundary(null)}>
          Show all
        </button>
      )}
    </form>
  );
}
