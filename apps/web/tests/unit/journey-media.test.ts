import { expect, it } from "vitest";
import { deriveJourney } from "../../src/features/journey/journey";
import { resolveMedia } from "../../src/features/discovery/media-registry";
import { fixture, orderedFixture } from "./fixtures";
it("requires one continuity and sourced, verified, unique order values", () => {
  expect(deriveJourney(orderedFixture(), null).available).toBe(false);
  expect(deriveJourney(fixture(), "c1").available).toBe(false);
  const data = orderedFixture();
  expect(deriveJourney(data, "c1").available).toBe(true);
  data.nodes[1].metadata.journey = {
    id: "j1",
    title: "Sourced test sequence",
    order: 0,
    source: "https://example.org/sequence",
    order_verified: true,
  };
  expect(deriveJourney(data, "c1").available).toBe(false);
});
it("does not derive chronology from array order, edges or a single event", () => {
  const data = orderedFixture();
  data.nodes[0].metadata = {};
  expect(deriveJourney(data, "c1").available).toBe(false);
});
it("requires consecutive journey entries to be connected", () => {
  const data = orderedFixture();
  data.edges = [];
  expect(deriveJourney(data, "c1").available).toBe(false);
});
it("provides permitted local artwork and a deterministic missing-media treatment", () => {
  expect(resolveMedia("a13997f9-a7a5-5468-85dc-130e52b12db3").kind).toBe(
    "interpretive",
  );
  expect(resolveMedia("unknown", "MYSTERY").src).toBe("/art/uncharted.svg");
  expect(resolveMedia("unknown", "MYSTERY").alt).toContain("mystery");
});
