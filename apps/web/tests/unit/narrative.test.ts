import { describe, expect, it } from "vitest";
import { createExplorationStore } from "../../src/stores/exploration";
import { LocalNarrativeDataProvider } from "../../src/features/narrative/provider";
import type { NarrativeDataProvider } from "../../src/features/narrative/contracts";
import { resolveNarrative } from "../../src/features/narrative/resolve";
import {
  NarrativeLayout,
  LoreRelationshipLayout,
} from "../../src/features/graph/layout-strategies";
import { narrativeGraph, narrativeFixture } from "./narrative-fixtures";
async function prepared(
  provider: NarrativeDataProvider = new LocalNarrativeDataProvider(
    narrativeFixture(),
  ),
) {
  const store = createExplorationStore(narrativeGraph(), provider);
  await store.getState().loadNarrative();
  return store;
}
describe("curated narrative and branches", () => {
  it("begins, progresses and bounds the explicit sequence", async () => {
    const store = await prepared();
    expect(store.getState().selectedId).toBe("a");
    expect(store.getState().layoutKind).toBe("narrative");
    store.getState().stepJourney(-1);
    expect(store.getState().journeyIndex).toBe(0);
    store.getState().stepJourney(1);
    expect(store.getState().selectedId).toBe("b");
    store.getState().stepJourney(50);
    expect(store.getState().selectedId).toBe("d");
    store.getState().stepJourney(1);
    expect(store.getState().journeyIndex).toBe(3);
    store.getState().beginJourney("intro", true);
    expect(store.getState().selectedId).toBe("a");
  });
  it("preserves journey position through a character and multiple lore discoveries", async () => {
    const store = await prepared();
    store.getState().stepJourney(1);
    store.getState().selectNode("person");
    expect(store.getState().mode).toBe("explore");
    expect(store.getState().journeyBookmark?.journeyIndex).toBe(1);
    store.getState().enterLore("thread");
    store.getState().selectDiscovery("reading");
    expect(store.getState().mode).toBe("lore");
    expect(store.getState().journeyIndex).toBe(1);
    expect(store.getState().currentDiscoveryId).toBe("reading");
    store.getState().resumeJourney();
    expect(store.getState().mode).toBe("guided");
    expect(store.getState().selectedId).toBe("b");
    store.getState().stepJourney(1);
    expect(store.getState().selectedId).toBe("c");
  });
  it("restores separate focus frames and camera pose when returning from a branch", async () => {
    const store = await prepared(),
      camera = { x: 0.7, y: 0.4, ratio: 0.6, angle: 0 };
    store.getState().stepJourney(1);
    store.getState().setCamera(camera);
    store.getState().selectNode("person");
    store.getState().enterLore("thread");
    store.getState().backFocus();
    expect(store.getState().selectedId).toBe("person");
    expect(store.getState().mode).toBe("explore");
    store.getState().backFocus();
    expect(store.getState().selectedId).toBe("b");
    expect(store.getState().mode).toBe("guided");
    expect(store.getState().cameraRequest.target).toEqual(camera);
  });
  it("resumes through mode switches and entering a known lore concept", async () => {
    const store = await prepared();
    store.getState().stepJourney(2);
    store.getState().selectNode("concept");
    expect(store.getState().mode).toBe("lore");
    store.getState().setMode("explore");
    store.getState().setMode("guided");
    expect(store.getState().journeyIndex).toBe(2);
    expect(store.getState().selectedId).toBe("c");
  });
  it("accepts a replacement asynchronous provider without changing presentation actions", async () => {
    const scopes: string[] = [];
    const replacement: NarrativeDataProvider = {
      load: async (scope) => {
        scopes.push(scope.universeId);
        return narrativeFixture();
      },
    };
    const store = await prepared(replacement);
    store.getState().stepJourney(1);
    expect(scopes).toEqual(["u1"]);
    expect(store.getState().selectedId).toBe("b");
  });
  it("ignores provider responses arriving after the universe changes", async () => {
    let release!: (catalog: ReturnType<typeof narrativeFixture>) => void;
    const pending = new Promise<ReturnType<typeof narrativeFixture>>(
      (resolve) => {
        release = resolve;
      },
    );
    const store = createExplorationStore(narrativeGraph(), {
      load: () => pending,
    });
    const loading = store.getState().loadNarrative();
    store.getState().beginUniverse({
      ...narrativeGraph().universe,
      id: "other",
      slug: "other",
    });
    release(narrativeFixture());
    await loading;
    expect(store.getState().narrative.journeys).toEqual([]);
    expect(store.getState().activeUniverse?.id).toBe("other");
  });
  it("clears history and scoped narrative on continuity changes", async () => {
    const store = await prepared();
    store.getState().stepJourney(1);
    store.getState().setContinuity("c2");
    expect(store.getState().activeJourneyId).toBeNull();
    expect(store.getState().focusHistory).toEqual([]);
    expect(store.getState().journeyBookmark).toBeNull();
  });
});
describe("reference validation and layout strategies", () => {
  it("rejects missing node references rather than constructing substitute story events", () => {
    const graph = narrativeGraph();
    graph.nodes = graph.nodes.filter((n) => n.id !== "b");
    const resolved = resolveNarrative(narrativeFixture(), graph, "c1");
    expect(resolved.catalog.journeys).toEqual([]);
    expect(resolved.catalog.loreThreads).toEqual([]);
    expect(resolved.issues.length).toBeGreaterThan(0);
  });
  it("does not merge adaptations or accept unknown citations", () => {
    const data = narrativeFixture();
    data.journeys[0].steps[0].sourceIds = ["missing"];
    expect(
      resolveNarrative(data, narrativeGraph(), "c1").catalog.journeys,
    ).toEqual([]);
    expect(
      resolveNarrative(narrativeFixture(), narrativeGraph(), "c2").catalog
        .journeys,
    ).toEqual([]);
  });
  it("keeps deterministic story coordinates independent of graph response ordering", () => {
    const graph = narrativeGraph(),
      data = narrativeFixture(),
      strategy = new NarrativeLayout();
    const context = {
      graph,
      journey: data.journeys[0],
      discoveries: data.discoveries,
      previous: new Map(),
    };
    const before = strategy.compute(context);
    const after = strategy.compute({
      ...context,
      graph: { ...graph, nodes: [...graph.nodes].reverse() },
    });
    expect([...before.entries()].sort()).toEqual([...after.entries()].sort());
    expect(
      new Set(["a", "b", "c", "d"].map((id) => before.get(id)?.x)).size,
    ).toBe(4);
    expect(
      new Set(["a", "b", "c", "d"].map((id) => before.get(id)?.y)).size,
    ).toBeGreaterThan(1);
  });
  it("preserves known coordinates and anchors the lore concept", () => {
    const graph = narrativeGraph(),
      data = narrativeFixture(),
      strategy = new LoreRelationshipLayout();
    const context = {
      graph,
      thread: data.loreThreads[0],
      discoveries: data.discoveries,
      previous: new Map(),
    };
    const before = strategy.compute(context);
    const after = strategy.compute({ ...context, previous: before });
    expect(after.get("concept")).toEqual({ x: 0, y: 0 });
    expect(after.get("b")).toEqual(before.get("b"));
    expect(after.get("question")).not.toEqual(after.get("b"));
  });
});
