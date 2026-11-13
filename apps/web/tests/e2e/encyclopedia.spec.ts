import { expect, test } from "@playwright/test";

test("opens a real scoped entry, follows sources and restores the story bookmark", async ({
  page,
  request,
}) => {
  const graph = await (
    await request.get("/api/atlas/universes/re-zero/graph")
  ).json();
  const continuity = graph.continuities[0].id;
  const params = `continuity_id=${continuity}`;
  const catalog = await (
    await request.get(`/api/atlas/universes/re-zero/narrative?${params}`)
  ).json();
  const character = catalog.entryIndex?.find(
    (entry: { id: string }) =>
      graph.nodes.find(
        (node: { id: string; type: string }) => node.id === entry.id,
      )?.type === "CHARACTER",
  );
  test.skip(
    !character,
    "Requires actual accepted research; no encyclopedia findings are fabricated.",
  );
  const entryResponse = await request.get(
    `/api/atlas/universes/re-zero/entries/${character.id}?${params}`,
  );
  expect(entryResponse.ok()).toBe(true);
  const entry = await entryResponse.json();
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  await expect(page.getByLabel("Open encyclopedia entry")).toBeVisible();
  await page.getByLabel("Open encyclopedia entry").selectOption(character.id);
  const panel = page.getByRole("complementary", { name: "Story information" });
  await expect(
    panel.getByRole("heading", { name: entry.display_title, exact: true }),
  ).toBeVisible();
  await panel.getByText(/Sources & evidence/).click();
  await expect(panel.getByRole("link").first()).toHaveAttribute(
    "href",
    /^https?:\/\//,
  );
  await page
    .getByRole("button", { name: "Return to journey", exact: false })
    .click();
  await expect(panel).toHaveCount(0);
  await page.getByLabel("Spoilers through episode").fill("1");
  await expect(page.getByLabel("Spoilers through episode")).toHaveValue("1");
  const bounded = await (
    await request.get(
      `/api/atlas/universes/re-zero/narrative?${params}&spoiler_position=1`,
    )
  ).json();
  await expect(
    page.getByLabel("Open encyclopedia entry").locator("option"),
  ).toHaveCount((bounded.entryIndex?.length ?? 0) + 1);
  await page.getByLabel("Spoilers through episode").fill("");
  await expect(
    page.getByLabel("Open encyclopedia entry").locator("option"),
  ).toHaveCount(catalog.entryIndex.length + 1);
});
