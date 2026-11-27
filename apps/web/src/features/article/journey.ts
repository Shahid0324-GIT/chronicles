import type {
  JourneyStep,
  NarrativeJourney,
  StorySection,
} from "@/features/narrative/contracts";

/** A place or chapter on the journey; hidden ones are beyond the reader's limit. */
export interface Stop {
  position: number;
  title: string;
  hidden: boolean;
}

export function journeyStops(journey: NarrativeJourney): Stop[] {
  const shown = (journey.stops ?? []).map((s) => ({ ...s, hidden: false }));
  const last = shown.at(-1)?.position ?? 0;
  const unseen = Math.max(
    0,
    (journey.stopCount ?? shown.length) - shown.length,
  );
  return [
    ...shown,
    ...Array.from({ length: unseen }, (_, i) => ({
      position: last + i + 1,
      title: "Hidden",
      hidden: true,
    })),
  ];
}

export const momentsAt = (steps: JourneyStep[], position: number) =>
  steps.filter((s) => s.position === position);

/** The article's sections, cut down to the paragraphs telling the given events. */
export function sectionsAt(story: StorySection[], eventIds: Set<string>) {
  let current: string[] = [];
  return story.flatMap((section, index) => {
    const paragraphs = section.paragraphs.filter((p) => {
      // A paragraph without events of its own continues the one before it.
      if (p.eventNodeIds.length) current = p.eventNodeIds;
      return current.some((id) => eventIds.has(id));
    });
    return paragraphs.length
      ? [{ heading: section.heading, index, paragraphs }]
      : [];
  });
}

export const STOP_GAP = 190;
const COLUMN = 250;
const ROW = 108;
const BRANCH_TOP = 250;

/** Columns and rows of a stop's moments: wide before it grows tall. */
export function branchShape(count: number) {
  const columns = Math.min(5, Math.ceil(count / 3) || 1);
  return { columns, rows: Math.ceil(count / columns) };
}

/** Room for the whole tree, so no branch is cut off. */
export const treeHeight = (count: number) =>
  Math.max(360, BRANCH_TOP + branchShape(count).rows * ROW + 50);

export interface TreeNode {
  id: string;
  kind: "stop" | "moment";
  x: number;
  y: number;
}
export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  kind: "path" | "ahead" | "branch" | "cause";
}

export const stopId = (position: number) => `stop-${position}`;

/**
 * The journey as a tree: stops wind from left to right, and the chosen stop grows its
 * moments in columns beneath it, with the story's stated causes drawn between them.
 */
export function journeyTree(
  stops: Stop[],
  moments: JourneyStep[],
  chosen: number,
  causes: { source: string; target: string }[],
) {
  const nodes: TreeNode[] = stops.map((stop, i) => ({
    id: stopId(stop.position),
    kind: "stop",
    x: i * STOP_GAP,
    y: i % 2 ? 80 : 0,
  }));
  const edges: TreeEdge[] = stops.slice(1).map((stop, i) => ({
    id: `path-${stop.position}`,
    source: stopId(stops[i].position),
    target: stopId(stop.position),
    kind: stop.hidden ? "ahead" : "path",
  }));
  const origin = nodes[stops.findIndex((s) => s.position === chosen)];
  if (!origin) return { nodes, edges };
  const { columns, rows } = branchShape(moments.length);
  // Centred under the stop, and never starting left of the first stop.
  const left = Math.max(-60, origin.x - ((columns - 1) * COLUMN) / 2 - 50);
  moments.forEach((moment, i) => {
    const column = Math.floor(i / rows),
      row = i % rows;
    nodes.push({
      id: moment.eventNodeId,
      kind: "moment",
      x: left + column * COLUMN,
      y: BRANCH_TOP + row * ROW,
    });
    edges.push({
      id: `branch-${moment.eventNodeId}`,
      source: row ? moments[i - 1].eventNodeId : origin.id,
      target: moment.eventNodeId,
      kind: "branch",
    });
  });
  const here = new Set(moments.map((m) => m.eventNodeId));
  const drawn = new Set(edges.map((e) => `${e.source}>${e.target}`));
  for (const cause of causes)
    if (
      here.has(cause.source) &&
      here.has(cause.target) &&
      !drawn.has(`${cause.source}>${cause.target}`)
    )
      edges.push({
        id: `cause-${cause.source}-${cause.target}`,
        source: cause.source,
        target: cause.target,
        kind: "cause",
      });
  return { nodes, edges };
}
