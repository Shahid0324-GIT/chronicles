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
  presentationState?: { status: string; reason: string };
  detailedRecap?: string;
  presentationStatus?: "validated" | "unavailable";
  underlyingEventIds?: string[];
  participantRoles?: {
    nodeId: string;
    role: "actor" | "recipient" | "witness" | "opponent";
  }[];
  id: string;
  position?: number;
  eventNodeId: string;
  title: string;
  body: string;
  episodeLabel: string;
  sourceIds: string[];
  loreThreadIds: string[];
  presentation: PresentationHint;
}
/** A run of article text; a nodeId makes it open that entry. */
export interface StorySegment {
  text: string;
  nodeId?: string;
}
export interface StoryParagraph {
  segments: StorySegment[];
  eventNodeIds: string[];
  sourceIds: string[];
}
export interface StorySection {
  heading: string;
  paragraphs: StoryParagraph[];
}
export type ThemeMotif =
  "stars" | "branches" | "waves" | "peaks" | "embers" | "rings";
/** A story's own look; colours arrive already checked for contrast. */
export interface StoryTheme {
  mode: "dark" | "light";
  ground: string;
  surface: string;
  ink: string;
  muted: string;
  line: string;
  accent: string;
  accentInk: string;
  second: string;
  style: "epic" | "storybook" | "gothic" | "scifi" | "playful" | "modern";
  motif: ThemeMotif;
}
export interface NarrativeJourney {
  theme?: StoryTheme;
  /** Stops reached so far, and how many the arc has in all. */
  stops?: { position: number; title: string }[];
  stopCount?: number;
  story?: StorySection[];
  positionWord?: string;
  presentationState?: { status: string; reason: string };
  overview?: string;
  id: string;
  universeId: string;
  continuityId: string;
  title: string;
  introduction: string;
  spoilerScope: string;
  ordering: {
    basis:
      | "broadcast-presentation"
      | "manga-chapter"
      | "story-position"
      | "unresolved";
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
  reconstruction?: {
    status: string;
    readingExplanation: string;
    coverage: {
      verifiedSegments: number;
      candidateTransitions: number;
      causallyExplainedTransitions: number;
      unexplainedTransitions: number;
      segmentsWithParticipants: number;
      segmentsWithLocations: number;
    };
    segments: {
      id: string;
      eventNodeIds: string[];
      title: string;
      statement: string;
    }[];
    transitions: {
      fromId: string;
      toId: string;
      explanation: string;
      sourceOrder: string;
      narrativeOrder: string;
      chronology: string;
    }[];
  };
  researchScopes?: {
    id: string;
    title: string;
    firstPosition: number;
    lastPosition: number;
    references: string[];
  }[];
  researchState?: {
    coverage?: string | null;
    status: string;
    jobId: string | null;
    error: string | null;
  };
  unorderedMilestones?: JourneyStep[];
  coverage?: {
    status: string;
    acceptedEvents: number;
    validatedMilestones: number;
    entries: number;
    orderingGaps: number;
  };
  relations?: { id: string; source: string; target: string; type: string }[];
  entryIndex?: { id: string; displayTitle: string }[];
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
  spoilerPosition?: number | null;
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
