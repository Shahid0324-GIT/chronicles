import type { GraphNode, UniverseGraph } from "../../src/lib/contracts";
// Synthetic test records only. The application never imports this module.
export const node = (
  id: string,
  type: GraphNode["type"] = "CHARACTER",
  continuity: string | null = "c1",
): GraphNode => ({
  id,
  universe_id: "u1",
  continuity_id: continuity,
  type,
  title: id,
  summary: "Test record",
  metadata: {},
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
});
export function fixture(): UniverseGraph {
  return {
    universe: {
      id: "u1",
      slug: "test-world",
      title: "Test World",
      description: "",
      created_at: "",
      updated_at: "",
    },
    continuities: [
      {
        id: "c1",
        universe_id: "u1",
        name: "Test anime",
        medium: "ANIME",
        description: "",
      },
      {
        id: "c2",
        universe_id: "u1",
        name: "Test novel",
        medium: "NOVEL",
        description: "",
      },
    ],
    nodes: [
      node("a"),
      node("b", "EVENT"),
      node("shared", "LORE", null),
      node("adaptation", "EVENT", "c2"),
    ],
    edges: [
      {
        id: "ab",
        universe_id: "u1",
        continuity_id: "c1",
        source: "a",
        target: "b",
        relationship_type: "PARTICIPATED_IN",
        description: "Test link",
      },
      {
        id: "bs",
        universe_id: "u1",
        continuity_id: "c1",
        source: "b",
        target: "shared",
        relationship_type: "REVEALED",
        description: "Test reveal",
      },
    ],
  };
}
export function orderedFixture(): UniverseGraph {
  const data = fixture();
  data.nodes[0] = { ...data.nodes[0], type: "EVENT" };
  for (const [index, item] of data.nodes.slice(0, 2).entries())
    item.metadata.journey = {
      id: "j1",
      title: "Sourced test sequence",
      order: index,
      source: "https://example.org/sequence",
      order_verified: true,
    };
  return data;
}
