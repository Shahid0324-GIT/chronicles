import { expect, test } from "@playwright/test";
import path from "node:path";
import { openUniverse } from "./universe";

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
    path: path.resolve("../../docs/evidence/increment-6-0/real-one-piece.png"),
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
    path: path.resolve(
      "../../docs/evidence/increment-6-0/real-one-piece-entry.png",
    ),
  });
});
