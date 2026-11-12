"use client";
import type { CSSProperties } from "react";
import { NODE_IDENTITIES, NODE_TYPES } from "@/features/graph/identity";
import { useExploration } from "@/stores/ExplorationProvider";
export default function LayerControls() {
  const types = useExploration((s) => s.types),
    toggle = useExploration((s) => s.toggleType),
    graph = useExploration((s) => s.graph);
  return (
    <div className="layer-controls glass">
      <span className="eyebrow">MAP LAYERS</span>
      <div>
        {NODE_TYPES.map((type) => {
          const visual = NODE_IDENTITIES[type];
          const count = graph?.nodes.filter((n) => n.type === type).length ?? 0;
          return (
            <button
              key={type}
              aria-label={`Show ${visual.label.toLowerCase()}`}
              aria-pressed={types.includes(type)}
              style={{ "--type-color": visual.color } as CSSProperties}
              onClick={() => toggle(type)}
            >
              <span aria-hidden="true">{visual.glyph}</span>
              {visual.label}
              <small>{count}</small>
            </button>
          );
        })}
      </div>
    </div>
  );
}
