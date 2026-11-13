export type ExplorationMode = "explore" | "guided" | "lore";
export type LayoutKind = "narrative" | "lore" | "free";
export interface SourceCitation {
  id: string;
  title: string;
  url: string;
  locator: string;
}
export interface PresentationHint {
  relatedNodeIds: string[];
  relationshipIds: string[];
  focusRatio?: number;
}
export interface JourneyStep {
  participantRoles?: {
    nodeId: string;
    role: "actor" | "recipient" | "witness" | "opponent";
  }[];
  id: string;
  eventNodeId: string;
  title: string;
  body: string;
  episodeLabel: string;
  sourceIds: string[];
  loreThreadIds: string[];
  presentation: PresentationHint;
}
export interface NarrativeJourney {
  id: string;
  universeId: string;
  continuityId: string;
  title: string;
  introduction: string;
  spoilerScope: string;
  ordering: {
    basis: "broadcast-presentation";
    explanation: string;
    sourceIds: string[];
  };
  steps: JourneyStep[];
}
export interface LoreThread {
  id: string;
  universeId: string;
  continuityId: string;
  conceptNodeId: string;
  title: string;
  introduction: string;
  spoilerScope: string;
  discoveryIds: string[];
  initialDiscoveryId: string;
  presentation: PresentationHint;
}
export interface Discovery {
  id: string;
  threadId: string;
  nodeId: string;
  title: string;
  explanation: string;
  classification: "established" | "interpretation" | "unresolved";
  sourceIds: string[];
  relatedDiscoveryIds: string[];
  presentation: PresentationHint;
}
export interface NarrativeCatalog {
  availability?: {
    kind: "generated" | "curated";
    reason: string;
    revision?: string;
    partial?: boolean;
    gapCount?: number;
  };
  schemaVersion: 1;
  journeys: NarrativeJourney[];
  loreThreads: LoreThread[];
  discoveries: Discovery[];
  sources: SourceCitation[];
}
export interface NarrativeScope {
  universeSlug?: string;
  universeId: string;
  continuityId: string | null;
}
export interface NarrativeDataProvider {
  load(scope: NarrativeScope, signal?: AbortSignal): Promise<NarrativeCatalog>;
}
export const emptyNarrativeCatalog = (): NarrativeCatalog => ({
  schemaVersion: 1,
  journeys: [],
  loreThreads: [],
  discoveries: [],
  sources: [],
});
