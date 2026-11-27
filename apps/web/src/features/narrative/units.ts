"use client";
import { useExploration } from "@/stores/ExplorationProvider";

/** What this story calls a step along it: chapter, episode, part and so on. */
export function usePositionUnit() {
  const named = useExploration(
    (s) =>
      s.narrative.journeys.find((j) => j.id === s.activeJourneyId)
        ?.positionWord,
  );
  const medium = useExploration((s) =>
    s.graph?.continuities
      .find((c) => c.id === s.continuityId)
      ?.medium.toUpperCase(),
  );
  if (named) return named;
  return medium === "MANGA" || medium === "NOVEL"
    ? "chapter"
    : medium === "ANIME"
      ? "episode"
      : "source position";
}
