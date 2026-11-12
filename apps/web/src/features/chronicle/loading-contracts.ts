import type { UniverseGraph } from "@/lib/contracts";
import type {
  NarrativeCatalog,
  NarrativeScope,
} from "@/features/narrative/contracts";
import type { BranchKind } from "./model";
/** Future provider seam, intentionally without an HTTP implementation or fake calls. */
export interface AtlasRegionRequest extends NarrativeScope {
  focus:
    | { kind: "overview" }
    | { kind: "milestones"; journeyId: string; aroundStepId: string }
    | { kind: "arc"; nodeId: string }
    | { kind: "branch"; eventNodeId: string; branch: BranchKind }
    | { kind: "related"; nodeId: string };
}
export interface AtlasRegion {
  key: string;
  revision: string;
  graph: UniverseGraph;
  narrative: NarrativeCatalog;
}
export interface AtlasRegionProvider {
  load(request: AtlasRegionRequest, signal?: AbortSignal): Promise<AtlasRegion>;
  release(regionKey: string): void;
}
