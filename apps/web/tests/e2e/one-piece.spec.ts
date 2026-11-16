import { expect, test } from "@playwright/test";
import path from "node:path";
import { openUniverse } from "./universe";

const evidenceDirectory =
  process.env.CHRONICLES_EVIDENCE_DIR ?? "test-results/one-piece";

test("displays actual One Piece research and exact source-backed partial state", async ({
  page,
  request,
}) => {
  const graphResponse = await request.get(
    "/api/atlas/universes/one-piece/graph",
  );
  expect(
    graphResponse.ok(),
    "Configure and research One Piece before the live acceptance suite",
  ).toBe(true);
  const graph = await graphResponse.json();
  const continuity = graph.continuities.find(
    (c: { medium: string }) => c.medium === "MANGA",
  );
  expect(continuity).toBeTruthy();
  const query = `continuity_id=${continuity.id}&spoiler_position=7`;
  const catalog = await (
    await request.get(`/api/atlas/universes/one-piece/narrative?${query}`)
  ).json();
  expect(
    catalog.entryIndex.length,
    "Real live research must supply reader-visible knowledge",
  ).toBeGreaterThan(0);
  await page.setViewportSize({ width: 1920, height: 1080 });
  await openUniverse(page, /^One Piece/, continuity.id);
  await page.getByLabel("Spoilers through chapter").fill("7");
  await expect(
    page.getByRole("heading", { name: "Romance Dawn", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Open encyclopedia entry").locator("option"),
  ).toHaveCount(catalog.entryIndex.length + 1);
  await expect(
    page.getByText("Story account pending", { exact: true }),
  ).toHaveCount(0);
  await page.screenshot({
    path: path.resolve(evidenceDirectory, "real-one-piece.png"),
  });
  expect(catalog.reconstruction.status).toBe("partial");
  expect(catalog.reconstruction.coverage.verifiedSegments).toBeGreaterThan(1);
  expect(
    catalog.reconstruction.coverage.unexplainedTransitions,
  ).toBeGreaterThan(0);
  const reconstruction = page.getByRole("region", {
    name: "Story reconstruction",
  });
  await reconstruction.locator("summary").click();
  await expect(reconstruction).toContainText(
    "do not establish narrative order",
  );
  await reconstruction.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.resolve(evidenceDirectory, "real-reconstruction.png"),
  });
  const item = catalog.entryIndex[0];
  const entry = await (
    await request.get(
      `/api/atlas/universes/one-piece/entries/${item.id}?${query}`,
    )
  ).json();
  expect(entry.source_references.length).toBeGreaterThan(0);
  expect(graph.nodes.some((n: { id: string }) => n.id === item.id)).toBe(true);
  await page.getByLabel("Open encyclopedia entry").selectOption(item.id);
  const panel = page.getByRole("complementary", { name: "Story information" });
  await expect(
    panel.getByRole("heading", { name: entry.display_title, exact: true }),
  ).toBeVisible();
  await panel.getByText(/Sources & evidence/).click();
  await expect(panel.getByRole("link").first()).toHaveAttribute(
    "href",
    /^https:\/\//,
  );
  await page.screenshot({
    path: path.resolve(evidenceDirectory, "real-one-piece-entry.png"),
  });
});

test("opens real researched characters and preserves chapter-fenced connections", async ({
  page,
  request,
}) => {
  const graph = await (
    await request.get("/api/atlas/universes/one-piece/graph")
  ).json();
  const manga = graph.continuities.find(
    (c: { medium: string }) => c.medium === "MANGA",
  );
  const query = `continuity_id=${manga.id}&spoiler_position=1`;
  const catalog = await (
    await request.get(`/api/atlas/universes/one-piece/narrative?${query}`)
  ).json();
  const luffy = graph.nodes.filter(
    (n: { type: string; title: string }) =>
      n.type === "CHARACTER" && n.title === "Luffy",
  );
  const shanks = graph.nodes.filter(
    (n: { type: string; title: string }) =>
      n.type === "CHARACTER" && n.title === "Shanks",
  );
  expect(luffy).toHaveLength(1);
  expect(shanks).toHaveLength(1);
  expect(
    graph.edges.some(
      (e: { source: string; target: string; relationship_type: string }) =>
        e.relationship_type === "RELATED_TO" &&
        e.source === shanks[0].id &&
        e.target === luffy[0].id,
    ),
  ).toBe(true);
  const steps = [
    ...catalog.journeys.flatMap(
      (j: { steps: { eventNodeId: string }[] }) => j.steps,
    ),
    ...catalog.unorderedMilestones,
  ];
  expect(
    steps.some(
      (s: { eventNodeId: string }) =>
        s.eventNodeId === "dd6117bb-b626-5ead-b888-0ae7ac12c265",
    ),
  ).toBe(false);
  const entry = await (
    await request.get(
      `/api/atlas/universes/one-piece/entries/${luffy[0].id}?${query}`,
    )
  ).json();
  expect(entry.source_references.length).toBeGreaterThan(0);
  expect(entry.connections.length).toBeGreaterThan(0);
  await page.setViewportSize({ width: 1920, height: 1080 });
  await openUniverse(page, /^One Piece/, manga.id);
  await page.getByLabel("Spoilers through chapter").fill("1");
  await expect(
    page
      .getByLabel("Open encyclopedia entry")
      .locator(`option[value="${luffy[0].id}"]`),
  ).toHaveCount(1);
  await page.getByLabel("Open encyclopedia entry").selectOption(luffy[0].id);
  const panel = page.getByRole("complementary", { name: "Story information" });
  await expect(
    panel.getByRole("heading", { name: entry.display_title, exact: true }),
  ).toBeVisible();
  await expect(panel).toContainText(/Shanks/);
  await page.screenshot({
    path: path.resolve(evidenceDirectory, "real-character.png"),
  });
});
