import { expect, it } from "vitest";
import { createExplorationStore } from "../../src/stores/exploration";
import { fixture, orderedFixture } from "./fixtures";

it("leaves guided progression when choosing a free-exploration node or a layer", () => {
  const store = createExplorationStore(orderedFixture());
  store.getState().setMode("guided");
  store.getState().stepJourney(1);
  expect(store.getState().mode).toBe("guided");
  store.getState().selectNode("shared");
  expect(store.getState().mode).toBe("explore");
  store.getState().setMode("guided");
  store.getState().toggleType("LORE");
  expect(store.getState().mode).toBe("explore");
});

it("re-evaluates guided ordering when continuity changes", () => {
  const store = createExplorationStore(orderedFixture());
  store.getState().setMode("guided");
  store.getState().stepJourney(1);
  store.getState().setContinuity("c2");
  expect(store.getState().selectedId).toBeNull();
  store.getState().setContinuity("c1");
  expect(store.getState().selectedId).toBe("a");
  expect(store.getState().journeyIndex).toBe(0);
});

it("deduplicates incoming edges and rejects incompatible or missing endpoints", () => {
  const data = fixture(),
    store = createExplorationStore(data);
  for (const edge of [
    data.edges[0],
    { ...data.edges[0], id: "missing", target: "absent" },
    { ...data.edges[0], id: "cross-continuity", target: "adaptation" },
  ]) {
    store
      .getState()
      .consume({ type: "relationship.added", universeId: "u1", edge });
  }
  expect(store.getState().graph?.edges).toHaveLength(2);
  store.getState().consume({
    type: "relationship.added",
    universeId: "u1",
    edge: { ...data.edges[0], id: "new-edge" },
  });
  expect(store.getState().graph?.edges).toHaveLength(3);
});
