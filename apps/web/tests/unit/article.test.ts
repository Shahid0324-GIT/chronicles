import { describe, expect, it } from "vitest";
import {
  eventsAt,
  readingIndex,
  readingMinutes,
} from "@/features/article/model";
import { decodeNarrative } from "@/features/narrative/decode";
import { resolveNarrative } from "@/features/narrative/resolve";
import {
  journeyStops,
  journeyTree,
  momentsAt,
  sectionsAt,
} from "@/features/article/journey";
import type {
  NarrativeJourney,
  StorySection,
} from "@/features/narrative/contracts";
import type { UniverseGraph } from "@/lib/contracts";

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const universe = id(1),
  continuity = id(2),
  event = id(3),
  person = id(4),
  source = id(5);

const story: StorySection[] = [
  {
    heading: "Setting out",
    paragraphs: [
      {
        segments: [
          { text: "Mira", nodeId: person },
          { text: " left the harbor." },
        ],
        eventNodeIds: [event],
        sourceIds: [source],
      },
      {
        segments: [{ text: "The water rose." }],
        eventNodeIds: [],
        sourceIds: [],
      },
    ],
  },
];

const catalog = {
  schemaVersion: 1,
  sources: [
    {
      id: source,
      title: "Chapter 1",
      url: "https://example.org/1",
      locator: "x",
    },
  ],
  journeys: [
    {
      id: id(6),
      universeId: universe,
      continuityId: continuity,
      title: "The Search",
      introduction: "Mira searches.",
      spoilerScope: "Draft",
      ordering: {
        basis: "manga-chapter",
        explanation: "Draft order",
        sourceIds: [source],
      },
      steps: [
        {
          id: id(7),
          eventNodeId: event,
          title: "Departure",
          body: "Mira leaves.",
          episodeLabel: "By chapter 1",
          sourceIds: [source],
          loreThreadIds: [],
          presentation: { relatedNodeIds: [], relationshipIds: [] },
        },
      ],
      story,
    },
  ],
  loreThreads: [],
  discoveries: [],
};

const graph = {
  universe: { id: universe },
  nodes: [
    {
      id: event,
      universe_id: universe,
      continuity_id: continuity,
      type: "EVENT",
    },
  ],
  edges: [],
  continuities: [],
} as unknown as UniverseGraph;

describe("arc article", () => {
  it("accepts a story and rejects a malformed one", () => {
    expect(decodeNarrative(catalog).journeys[0].story).toHaveLength(1);
    const broken = structuredClone(catalog);
    broken.journeys[0].story[0].paragraphs[0].segments[0].nodeId = "nobody";
    expect(() => decodeNarrative(broken)).toThrow();
  });

  it("keeps the words of a name whose entry the graph does not hold", () => {
    const { catalog: resolved } = resolveNarrative(
      decodeNarrative(catalog),
      graph,
      continuity,
    );
    expect(resolved.journeys[0].story?.[0].paragraphs[0].segments[0]).toEqual({
      text: "Mira",
    });
  });

  it("follows the reader through the events", () => {
    expect(eventsAt(story, "0-1")).toEqual([event]);
    expect(readingIndex([-400, 100, 900], 300, false)).toBe(1);
    expect(readingIndex([-400, 100, 900], 300, true)).toBe(2);
    expect(readingMinutes(story)).toBe(1);
  });
});

describe("journey tree", () => {
  const moment = (n: number, position: number) => ({
    id: id(20 + n),
    eventNodeId: id(40 + n),
    position,
    title: "Moment " + n,
    body: "",
    episodeLabel: "",
    sourceIds: [],
    loreThreadIds: [],
    presentation: { relatedNodeIds: [], relationshipIds: [] },
  });
  const journey = {
    ...catalog.journeys[0],
    stops: [
      { position: 1, title: "Harbor" },
      { position: 2, title: "Marsh" },
    ],
    stopCount: 4,
    steps: [1, 2, 3, 4, 5].map((n) => moment(n, n === 1 ? 1 : 2)),
  } as unknown as NarrativeJourney;

  it("keeps unreached stops as hidden places", () => {
    expect(journeyStops(journey).map((s) => [s.position, s.hidden])).toEqual([
      [1, false],
      [2, false],
      [3, true],
      [4, true],
    ]);
  });

  it("grows the chosen stop's moments with only its stated causes", () => {
    const stops = journeyStops(journey);
    const moments = momentsAt(journey.steps, 2);
    const tree = journeyTree(stops, moments, 2, [
      { source: id(42), target: id(45) },
      { source: id(41), target: id(42) },
    ]);
    expect(tree.nodes.filter((n) => n.kind === "moment")).toHaveLength(4);
    expect(
      tree.edges.filter((e) => e.kind === "cause").map((e) => e.source),
    ).toEqual([id(42)]);
    expect(tree.edges.filter((e) => e.kind === "ahead")).toHaveLength(2);
    expect(new Set(tree.nodes.map((n) => `${n.x}:${n.y}`)).size).toBe(
      tree.nodes.length,
    );
  });

  it("cuts the article down to one stop", () => {
    expect(sectionsAt(story, new Set([event]))[0].paragraphs).toHaveLength(2);
    expect(sectionsAt(story, new Set(["other"]))).toEqual([]);
  });

  it("accepts only plain colours in a theme", () => {
    const themed = structuredClone(catalog) as unknown as {
      journeys: { theme: Record<string, string> }[];
    };
    themed.journeys[0].theme = {
      mode: "dark",
      ground: "#101030",
      surface: "#181840",
      ink: "#ffffff",
      muted: "#ccccdd",
      line: "#333366",
      accent: "#ffc857",
      accentInk: "#111018",
      second: "#6cb8ff",
      style: "epic",
      motif: "stars",
    };
    expect(decodeNarrative(themed).journeys[0].theme?.motif).toBe("stars");
    themed.journeys[0].theme.accent = "url(https://example.org/x)";
    expect(() => decodeNarrative(themed)).toThrow();
  });
});
