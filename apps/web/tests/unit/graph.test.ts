import { describe, expect, it } from "vitest";
import { adaptGraph } from "../../src/features/graph/adapter";
import { layoutNodes } from "../../src/features/graph/layout";
import { filterGraph } from "../../src/features/graph/filter";
import { NODE_TYPES } from "../../src/features/graph/identity";
import { fixture, node } from "./fixtures";

describe("backend graph adapter", () => {
  it("preserves IDs, direction, relation vocabulary and node attributes", () => {
    const data = fixture(),
      result = adaptGraph(data);
    expect(result.issues).toEqual([]);
    expect(result.graph.order).toBe(4);
    expect(result.graph.extremities("ab")).toEqual(["a", "b"]);
    expect(
      result.graph.getEdgeAttribute("ab", "entity").relationship_type,
    ).toBe("PARTICIPATED_IN");
    expect(result.graph.getNodeAttribute("a", "entity")).toEqual(data.nodes[0]);
    expect(result.graph.getNodeAttribute("a", "shape")).not.toBe(
      result.graph.getNodeAttribute("b", "shape"),
    );
  });
  it("supports parallel edges and cycles without turning the graph into a tree", () => {
    const data = fixture();
    data.edges.push(
      { ...data.edges[0], id: "parallel" },
      { ...data.edges[0], id: "reverse", source: "b", target: "a" },
    );
    expect(adaptGraph(data).graph.size).toBe(4);
  });
  it("rejects dangling, cross-universe and incompatible-continuity edges", () => {
    const data = fixture();
    data.edges.push(
      { ...data.edges[0], id: "dangling", target: "missing" },
      { ...data.edges[0], id: "cross", universe_id: "other" },
      { ...data.edges[0], id: "adapted", target: "adaptation" },
    );
    const result = adaptGraph(data);
    expect(result.graph.size).toBe(2);
    expect(result.issues).toHaveLength(3);
  });
  it("handles empty graphs and missing artwork", () => {
    const data = fixture();
    data.nodes = [];
    data.edges = [];
    expect(adaptGraph(data).graph.order).toBe(0);
    expect(adaptGraph(fixture()).graph.getNodeAttribute("a", "image")).toBe(
      "/art/uncharted.svg",
    );
  });
  it("has deterministic layout independent of response ordering", () => {
    const data = fixture();
    data.nodes.push(node("z"), node("y"));
    const a = layoutNodes(data.nodes, data.edges);
    const b = layoutNodes([...data.nodes].reverse(), [...data.edges].reverse());
    expect([...a.entries()].sort()).toEqual([...b.entries()].sort());
  });
  it("preserves known positions during incremental insertions", () => {
    const data = fixture(),
      before = layoutNodes(data.nodes, data.edges);
    const after = layoutNodes([...data.nodes, node("new")], data.edges, before);
    expect(after.get("a")).toEqual(before.get("a"));
    expect(after.has("new")).toBe(true);
  });
  it("filters continuity and types with induced edges, retaining shared nodes", () => {
    const result = filterGraph(fixture(), "c1", NODE_TYPES);
    expect(result.nodes.map((n) => n.id)).toEqual(["a", "b", "shared"]);
    const filtered = filterGraph(fixture(), "c1", ["CHARACTER", "LORE"]);
    expect(filtered.edges).toEqual([]);
    expect(filterGraph(fixture(), "c1", []).nodes).toEqual([]);
  });
});
