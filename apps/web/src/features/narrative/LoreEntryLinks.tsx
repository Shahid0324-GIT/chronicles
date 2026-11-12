"use client";
import { useExploration } from "@/stores/ExplorationProvider";
export default function LoreEntryLinks({ nodeId }: { nodeId: string }) {
  const narrative = useExploration((s) => s.narrative),
    enter = useExploration((s) => s.enterLore);
  const threads = narrative.loreThreads.filter(
    (t) =>
      t.conceptNodeId === nodeId ||
      t.presentation.relatedNodeIds.includes(nodeId) ||
      narrative.discoveries.some(
        (d) =>
          d.threadId === t.id &&
          (d.nodeId === nodeId ||
            d.presentation.relatedNodeIds.includes(nodeId)),
      ),
  );
  if (!threads.length) return null;
  return (
    <div className="lore-entry-links">
      <p className="eyebrow">A THREAD BENEATH THE STORY</p>
      {threads.map((t) => (
        <button key={t.id} onClick={() => enter(t.id)}>
          <span aria-hidden="true">◎</span> Investigate {t.title}
          <span aria-hidden="true">↗</span>
        </button>
      ))}
    </div>
  );
}
