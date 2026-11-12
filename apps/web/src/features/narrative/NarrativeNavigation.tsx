"use client";
import { useExploration } from "@/stores/ExplorationProvider";
import { activeJourney, activeThread } from "./selectors";
import type { LayoutKind } from "./contracts";
export default function NarrativeNavigation() {
  const length = useExploration((s) => s.focusHistory.length),
    back = useExploration((s) => s.backFocus),
    kind = useExploration((s) => s.layoutKind),
    layout = useExploration((s) => s.setLayout);
  const journey = useExploration(activeJourney),
    thread = useExploration(activeThread);
  return (
    <div className="narrative-navigation glass">
      <button
        aria-label="Back to previous focus"
        title="Back to previous focus"
        disabled={!length}
        onClick={back}
      >
        ←
      </button>
      <label>
        <span className="sr-only">Map layout</span>
        <select
          aria-label="Map layout"
          value={kind}
          onChange={(e) => layout(e.target.value as LayoutKind)}
        >
          <option value="narrative" disabled={!journey}>
            Story map
          </option>
          <option value="lore" disabled={!thread}>
            Lore map
          </option>
          <option value="free">Free map</option>
        </select>
      </label>
    </div>
  );
}
