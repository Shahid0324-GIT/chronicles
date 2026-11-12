"use client";
import IconButton from "@/components/ui/IconButton";
import { useExploration } from "@/stores/ExplorationProvider";
export default function MapControls() {
  const request = useExploration((s) => s.requestCamera),
    clear = useExploration((s) => s.clearSelection),
    ratio = useExploration((s) => s.camera.ratio);
  return (
    <div className="map-controls glass" aria-label="Map controls">
      <IconButton label="Zoom in" onClick={() => request("zoom-in")}>
        ＋
      </IconButton>
      <span className="zoom-value">{Math.round(100 / ratio)}%</span>
      <IconButton label="Zoom out" onClick={() => request("zoom-out")}>
        −
      </IconButton>
      <span className="control-divider" />
      <IconButton label="Return to full map" onClick={clear}>
        ⌖
      </IconButton>
    </div>
  );
}
