import { expect, it } from "vitest";
import { createExplorationStore } from "../../src/stores/exploration";
import { fixture } from "./fixtures";
it("selects actual directed relationships and clears stale edge details", () => {
  const store = createExplorationStore(fixture());
  store.getState().selectEdge("ab");
  expect(store.getState().selectedId).toBe("a");
  expect(store.getState().selectedEdgeId).toBe("ab");
  store.getState().selectEdge("ab");
  expect(store.getState().selectedId).toBe("b");
  store.getState().selectNode("shared");
  expect(store.getState().selectedEdgeId).toBeNull();
  store.getState().toggleType("CHARACTER");
  store.getState().selectEdge("ab");
  expect(store.getState().selectedEdgeId).toBeNull();
});
