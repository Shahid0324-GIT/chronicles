import { describe, expect, it, vi } from "vitest";
import { decodeEntry } from "../../src/features/narrative/encyclopedia";
import {
  BackendNarrativeDataProvider,
  LocalNarrativeDataProvider,
} from "../../src/features/narrative/provider";
import { narrativeFixture, narrativeGraph } from "./narrative-fixtures";
import { readerGraph } from "../../src/features/narrative/reader-graph";
import { createExplorationStore } from "../../src/stores/exploration";

describe("scoped encyclopedia reader", () => {
  it("rejects malformed nested entries and unsafe source URLs", () => {
    expect(() => decodeEntry({ id: "not-an-id" })).toThrow();
    const entry = {
      id: "00000000-0000-4000-8000-000000000001",
      display_title: "Owned entry",
      short_introduction: "Owned statement",
      aliases: [],
      sections: [],
      connections: [],
      source_references: [],
    };
    expect(decodeEntry(entry).display_title).toBe("Owned entry");
    expect(() =>
      decodeEntry({
        ...entry,
        source_references: [
          {
            id: entry.id,
            title: "Owned",
            url: "javascript:alert(1)",
            locator: "Owned",
          },
        ],
      }),
    ).toThrow();
    expect(() =>
      decodeEntry({
        ...entry,
        sections: [{ name: "history", statements: ["invalid"] }],
      }),
    ).toThrow();
  });
  it("never substitutes a broad curated catalog when a bounded request fails", async () => {
    const fixture = narrativeFixture();
    const request = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 503 }));
    const result = await new BackendNarrativeDataProvider(
      new LocalNarrativeDataProvider(fixture),
      request,
    ).load({
      universeId: fixture.journeys[0].universeId,
      continuityId: fixture.journeys[0].continuityId,
      universeSlug: "owned",
      spoilerPosition: 1,
    });
    expect(result.journeys).toEqual([]);
    expect(result.availability?.kind).toBe("generated");
    expect(request.mock.calls[0][0]).toContain("spoiler_position=1");
  });
  it("filters free graph names and traversable edges through the scoped backend index", () => {
    const graph = narrativeGraph(),
      catalog = narrativeFixture();
    const node = graph.nodes[0],
      other = graph.nodes[1];
    catalog.entryIndex = [
      { id: node.id, displayTitle: "Owned English name" },
      { id: other.id, displayTitle: "Another owned name" },
    ];
    catalog.relations = [];
    const projected = readerGraph(graph, catalog, 1);
    expect(projected.nodes).toHaveLength(2);
    expect(projected.nodes[0].title).toBe("Owned English name");
    expect(projected.edges).toEqual([]);
    expect(readerGraph(graph, catalog, null)).toBe(graph);
    expect(graph.nodes[0].title).toBe(node.title);
  });
  it("clears older reader content immediately when changing spoiler scope", async () => {
    const store = createExplorationStore(narrativeGraph(), {
      load: async () => new Promise(() => {}),
    });
    store.setState({ narrative: narrativeFixture() });
    store.getState().setSpoilerPosition(1);
    expect(store.getState().narrative.journeys).toEqual([]);
    expect(store.getState().selectedId).toBeNull();
    expect(store.getState().spoilerPosition).toBe(1);
    store.getState().selectNode("person");
    expect(store.getState().selectedId).toBeNull();
  });
});
