import { describe, expect, it } from "vitest";
import {
  eventsAt,
  eventTargets,
  readingIndex,
  readingMinutes,
} from "@/features/article/model";
import { decodeNarrative } from "@/features/narrative/decode";
import { resolveNarrative } from "@/features/narrative/resolve";
import type { StorySection } from "@/features/narrative/contracts";
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
    expect(eventTargets(story).get(event)).toBe("0-0");
    expect(eventsAt(story, "0-1")).toEqual([event]);
    expect(readingIndex([-400, 100, 900], 300, false)).toBe(1);
    expect(readingIndex([-400, 100, 900], 300, true)).toBe(2);
    expect(readingMinutes(story)).toBe(1);
  });
});
