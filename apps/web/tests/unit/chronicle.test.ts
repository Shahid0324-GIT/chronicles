import { describe, expect, it } from "vitest";
import { eventRegion, spineLayout } from "../../src/features/chronicle/model";
import {
  themeForUniverse,
  themeStyle,
} from "../../src/features/chronicle/design";
import { createExplorationStore } from "../../src/stores/exploration";
import { LocalNarrativeDataProvider } from "../../src/features/narrative/provider";
import { narrativeFixture, narrativeGraph } from "./narrative-fixtures";

async function ready() {
  const store = createExplorationStore(
    narrativeGraph(),
    new LocalNarrativeDataProvider(narrativeFixture()),
  );
  await store.getState().loadNarrative();
  return store;
}
describe("illustrated story presentation", () => {
  it("distinguishes explicit story progression from causal graph claims", () => {
    const graph = narrativeGraph(),
      catalog = narrativeFixture(),
      step = catalog.journeys[0].steps[1];
    const region = eventRegion(graph, step, catalog, "c1");
    expect(region.causes).toEqual([]);
    expect(region.consequences).toEqual([]);
    graph.edges = graph.edges.map((edge) =>
      ["edge-0", "edge-1"].includes(edge.id)
        ? { ...edge, relationship_type: "CAUSED" }
        : edge,
    );
    const causal = eventRegion(graph, step, catalog, "c1");
    expect(causal.causes.map((link) => link.node.id)).toEqual(["a"]);
    expect(causal.consequences.map((link) => link.node.id)).toEqual(["c"]);
  });
  it("keeps related branch entities in the current universe and continuity", () => {
    const graph = narrativeGraph(),
      catalog = narrativeFixture();
    graph.nodes = graph.nodes.map((node) =>
      node.id === "person" ? { ...node, continuity_id: "c2" } : node,
    );
    expect(
      eventRegion(graph, catalog.journeys[0].steps[1], catalog, "c1")
        .characters,
    ).toEqual([]);
    graph.nodes = graph.nodes.map((node) =>
      node.id === "person"
        ? { ...node, continuity_id: null, universe_id: "other" }
        : node,
    );
    expect(
      eventRegion(graph, catalog.journeys[0].steps[1], catalog, "c1")
        .characters,
    ).toEqual([]);
  });
  it("keeps the horizontal spine stable on focus changes within its visible window", () => {
    const journey = narrativeFixture().journeys[0];
    const before = spineLayout(journey, 0),
      after = spineLayout(journey, 2);
    expect(after.map((item) => item.x)).toEqual(before.map((item) => item.x));
    expect(after.map((item) => item.position)).toEqual([
      "earlier",
      "earlier",
      "current",
      "upcoming",
    ]);
    expect(
      after.every((item, index) => !index || item.x > after[index - 1].x),
    ).toBe(true);
  });
  it("windows longer journeys without removing their underlying steps", () => {
    const journey = narrativeFixture().journeys[0];
    journey.steps = Array.from({ length: 20 }, (_, index) => ({
      ...journey.steps[0],
      id: "step-" + index,
    }));
    const view = spineLayout(journey, 12);
    expect(view).toHaveLength(5);
    expect(view.find((item) => item.position === "current")?.index).toBe(12);
    expect(journey.steps).toHaveLength(20);
  });
  it("uses configurable universe themes and a stable fallback", () => {
    expect(themeForUniverse("re-zero").motif).toBe("arch");
    expect(themeForUniverse("one-piece").motif).toBe("chart");
    expect(themeForUniverse("elden-ring").motif).toBe("rune");
    expect(themeForUniverse("unknown")).toEqual(themeForUniverse());
    expect(themeStyle(themeForUniverse("re-zero"))).toHaveProperty(
      "--chronicle-accent",
    );
  });
  it("opens and collapses event branches while retaining their originating moment", async () => {
    const store = await ready();
    store.getState().selectMilestone(1);
    store.getState().toggleBranch("characters");
    expect(store.getState().expandedBranch).toBe("characters");
    store.getState().selectNode("person");
    store.getState().enterLore("thread");
    store.getState().selectDiscovery("unknown");
    expect(store.getState().journeyIndex).toBe(1);
    expect(store.getState().expandedBranch).toBe("lore");
    store.getState().resumeJourney();
    expect(store.getState().journeyIndex).toBe(1);
    expect(store.getState().selectedId).toBe("b");
    expect(store.getState().expandedBranch).toBeNull();
    store.getState().toggleBranch("characters");
    store.getState().toggleBranch("characters");
    expect(store.getState().expandedBranch).toBeNull();
  });
  it("restores branch expansion through history and clears it after scope changes", async () => {
    const store = await ready();
    store.getState().selectMilestone(1);
    store.getState().toggleBranch("characters");
    store.getState().selectNode("person");
    store.getState().backFocus();
    expect(store.getState().expandedBranch).toBe("characters");
    expect(store.getState().eventExpanded).toBe(true);
    store.getState().setContinuity("c2");
    expect(store.getState().expandedBranch).toBeNull();
    expect(store.getState().eventExpanded).toBe(false);
  });
  it("rejects invalid milestones and keeps rapid selections coherent", async () => {
    const store = await ready();
    for (const index of [1, 2, 0, 3, 1])
      store.getState().selectMilestone(index);
    for (const index of [-1, 4, NaN, 1.5])
      store.getState().selectMilestone(index);
    expect(store.getState().journeyIndex).toBe(1);
    expect(store.getState().selectedId).toBe("b");
    store.getState().toggleUpcoming();
    expect(store.getState().showUpcoming).toBe(false);
    expect(store.getState().journeyIndex).toBe(1);
  });
});
