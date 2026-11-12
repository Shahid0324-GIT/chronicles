"use client";
// Compatibility export for the Phase 1 rendering boundary.
import type { UniverseGraph } from "@/lib/contracts";
import AtlasExperience from "@/features/atlas/AtlasExperience";
export default function Atlas({ graph }: { graph: UniverseGraph }) {
  return <AtlasExperience universes={[graph.universe]} graph={graph} />;
}
