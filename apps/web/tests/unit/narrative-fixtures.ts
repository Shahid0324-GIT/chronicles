import type { NarrativeCatalog } from "../../src/features/narrative/contracts";
import { fixture, node } from "./fixtures";
export function narrativeGraph() {
  const graph = fixture();
  graph.nodes = [
    node("a", "EVENT"),
    node("b", "EVENT"),
    node("c", "EVENT"),
    node("d", "EVENT"),
    node("person"),
    node("concept", "LORE"),
    node("question", "MYSTERY"),
  ];
  graph.edges = [
    ["a", "b"],
    ["b", "c"],
    ["c", "d"],
    ["person", "b"],
    ["concept", "b"],
    ["concept", "question"],
  ].map(([source, target], index) => ({
    id: "edge-" + index,
    universe_id: "u1",
    continuity_id: "c1",
    source,
    target,
    relationship_type: "CONNECTED_TO" as const,
    description: "Synthetic test connection",
  }));
  return graph;
}
export function narrativeFixture(): NarrativeCatalog {
  return {
    schemaVersion: 1,
    sources: [
      {
        id: "source",
        title: "Synthetic citation",
        url: "https://example.org/test",
        locator: "A test-only source reference",
      },
    ],
    journeys: [
      {
        id: "intro",
        universeId: "u1",
        continuityId: "c1",
        title: "Test introduction",
        introduction: "Test",
        spoilerScope: "Test scope",
        ordering: {
          basis: "broadcast-presentation",
          explanation: "Explicit test order",
          sourceIds: ["source"],
        },
        steps: ["a", "b", "c", "d"].map((eventNodeId, index) => ({
          id: "step-" + index,
          eventNodeId,
          title: "Moment " + index,
          body: "Synthetic editorial note",
          episodeLabel: "Test episode",
          sourceIds: ["source"],
          loreThreadIds: ["thread"],
          presentation: {
            relatedNodeIds: ["person", "concept"],
            relationshipIds: [],
            focusRatio: 0.9,
          },
        })),
      },
    ],
    loreThreads: [
      {
        id: "thread",
        universeId: "u1",
        continuityId: "c1",
        title: "Test thread",
        conceptNodeId: "concept",
        introduction: "Test investigation",
        spoilerScope: "Test scope",
        initialDiscoveryId: "observation",
        discoveryIds: ["observation", "reading", "unknown"],
        presentation: {
          relatedNodeIds: ["person", "b", "question"],
          relationshipIds: ["edge-4", "edge-5"],
        },
      },
    ],
    discoveries: [
      {
        id: "observation",
        threadId: "thread",
        nodeId: "b",
        title: "Observation",
        explanation: "A test observation",
        classification: "established",
        sourceIds: ["source"],
        relatedDiscoveryIds: ["reading", "unknown"],
        presentation: {
          relatedNodeIds: ["concept"],
          relationshipIds: ["edge-4"],
        },
      },
      {
        id: "reading",
        threadId: "thread",
        nodeId: "person",
        title: "Reading",
        explanation: "A test interpretation",
        classification: "interpretation",
        sourceIds: ["source"],
        relatedDiscoveryIds: ["unknown"],
        presentation: { relatedNodeIds: ["b"], relationshipIds: ["edge-3"] },
      },
      {
        id: "unknown",
        threadId: "thread",
        nodeId: "question",
        title: "Question",
        explanation: "Unresolved in the test",
        classification: "unresolved",
        sourceIds: ["source"],
        relatedDiscoveryIds: ["observation"],
        presentation: {
          relatedNodeIds: ["concept"],
          relationshipIds: ["edge-5"],
        },
      },
    ],
  };
}
