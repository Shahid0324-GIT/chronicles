import { describe, expect, it } from "vitest";
import {
  createExplorationStore,
  DEFAULT_CAMERA,
} from "../../src/stores/exploration";
import { fixture, node, orderedFixture } from "./fixtures";
describe("exploration state", () => {
  it("keeps stores isolated and selection requests focus", () => {
    const a = createExplorationStore(fixture()),
      b = createExplorationStore(fixture());
    a.getState().selectNode("a");
    expect(a.getState().selectedId).toBe("a");
    expect(a.getState().cameraRequest.command).toBe("focus");
    expect(b.getState().selectedId).toBeNull();
    a.getState().clearSelection();
    expect(a.getState().cameraRequest.command).toBe("reset");
  });
  it("ignores missing, filtered and other-continuity selection", () => {
    const store = createExplorationStore(fixture());
    for (const id of ["missing", "adaptation"]) store.getState().selectNode(id);
    expect(store.getState().selectedId).toBeNull();
    store.getState().toggleType("CHARACTER");
    store.getState().selectNode("a");
    expect(store.getState().selectedId).toBeNull();
  });
  it("resets state and rejects stale or mismatched universe loads", () => {
    const data = fixture(),
      store = createExplorationStore(data);
    store.getState().selectNode("a");
    store.getState().setQuery("old");
    store.getState().setCamera({ ...DEFAULT_CAMERA, ratio: 0.4 });
    const next = {
      ...data,
      universe: { ...data.universe, id: "u2", slug: "other" },
    };
    const stale = store.getState().beginUniverse(data.universe);
    const token = store.getState().beginUniverse(next.universe);
    store.getState().completeUniverse(stale, data);
    expect(store.getState().graph).toBeNull();
    expect(store.getState().query).toBe("");
    expect(store.getState().camera).toEqual(DEFAULT_CAMERA);
    store.getState().completeUniverse(token, data);
    expect(store.getState().status).toBe("loading");
    store.getState().completeUniverse(token, next);
    expect(store.getState().activeUniverse?.id).toBe("u2");
    expect(store.getState().status).toBe("ready");
  });
  it("ignores stale failures and supports retry", () => {
    const data = fixture(),
      store = createExplorationStore(data);
    const stale = store.getState().beginUniverse(data.universe);
    const token = store.getState().beginUniverse(data.universe);
    store.getState().failUniverse(stale, "old");
    expect(store.getState().error).toBeNull();
    store.getState().failUniverse(token, "offline");
    expect(store.getState().status).toBe("error");
    const retry = store.getState().beginUniverse(data.universe);
    store.getState().completeUniverse(retry, data);
    expect(store.getState().status).toBe("ready");
  });
  it("clears selection when changing continuity or hidden layers", () => {
    const store = createExplorationStore(fixture());
    store.getState().selectNode("a");
    store.getState().setContinuity("c2");
    expect(store.getState().selectedId).toBeNull();
    store.getState().setContinuity("unknown");
    expect(store.getState().continuityId).toBe("c2");
  });
  it("does not pretend unordered data supports guided progression", () => {
    const store = createExplorationStore(fixture());
    store.getState().setMode("guided");
    store.getState().stepJourney(1);
    expect(store.getState().journeyIndex).toBe(0);
    expect(store.getState().selectedId).toBeNull();
  });
  it("progresses sourced connected events and bounds previous/next", () => {
    const store = createExplorationStore(orderedFixture());
    store.getState().setMode("guided");
    expect(store.getState().selectedId).toBe("a");
    store.getState().stepJourney(1);
    expect(store.getState().selectedId).toBe("b");
    store.getState().stepJourney(5);
    expect(store.getState().journeyIndex).toBe(1);
    store.getState().stepJourney(-10);
    expect(store.getState().selectedId).toBe("a");
    store.getState().setMode("explore");
    store.getState().stepJourney(1);
    expect(store.getState().mode).toBe("explore");
  });
  it("consumes incremental events only for the active universe", () => {
    const store = createExplorationStore(fixture());
    store
      .getState()
      .consume({ type: "node.added", universeId: "other", node: node("x") });
    expect(store.getState().graph?.nodes).toHaveLength(4);
    store
      .getState()
      .consume({ type: "node.added", universeId: "u1", node: node("x") });
    store.getState().consume({
      type: "node.updated",
      universeId: "u1",
      node: { ...node("x"), title: "Updated" },
    });
    store.getState().consume({
      type: "verification.changed",
      universeId: "u1",
      nodeId: "x",
      status: "verified",
    });
    expect(
      store.getState().graph?.nodes.find((n) => n.id === "x")?.metadata
        .verification_status,
    ).toBe("verified");
    store
      .getState()
      .consume({ type: "discovery.revealed", universeId: "u1", nodeId: "x" });
    expect(store.getState().discoveredIds).toEqual(["x"]);
    store.getState().consume({
      type: "research.progress",
      universeId: "u1",
      completed: 2,
      total: 1,
    });
    expect(store.getState().researchProgress).toBeNull();
  });
});
