import { expect, test } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import path from "node:path";

test("renders actual backend journey and preserves focus through graph refresh", async ({
  page,
  request,
}) => {
  const graph = await (
    await request.get("/api/atlas/universes/re-zero/graph")
  ).json();
  const continuity = graph.continuities[0].id;
  const response = await request.get(
    `/api/atlas/universes/re-zero/narrative?continuity_id=${continuity}`,
  );
  expect(response.ok()).toBe(true);
  const catalog = await response.json();
  test.skip(
    !catalog.journeys?.some((j: { steps: unknown[] }) => j.steps.length >= 2),
    "Requires an existing researched catalog; no seeded research is fabricated.",
  );
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  await expect(
    page.getByText("RESEARCHED JOURNEY", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: catalog.journeys[0].title, exact: true }),
  ).toBeVisible();
  const moments = page.getByRole("button", { name: /Open story moment/ });
  await expect(moments).toHaveCount(catalog.journeys[0].steps.length);
  await moments.nth(1).click();
  const selected = catalog.journeys[0].steps[1].title;
  await expect(
    page.getByRole("heading", { name: selected, exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await page
    .getByRole("button", { name: "Refresh story atlas", exact: true })
    .click();
  await page.getByRole("button", { name: "Close research" }).click();
  await expect(
    page.getByRole("heading", { name: selected, exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("Research archive", { exact: true }),
  ).toBeVisible();
});

test("starts a job and presents bounded progress without a dashboard (synthetic HTTP responses)", async ({
  page,
}) => {
  const jid = "00000000-0000-4000-8000-000000000030";
  await page.route("**/api/atlas/research/jobs", (route) =>
    route.fulfill({ json: { id: jid } }),
  );
  await page.route(`**/api/atlas/research/jobs/${jid}/summary`, (route) =>
    route.fulfill({
      json: {
        id: jid,
        status: "partial",
        stage: "narrative_builder",
        error: null,
        model_calls: 4,
        cache_hits: 1,
        retry_count: 0,
        validation_failures: 0,
        sources: 2,
        embedding_reused: 2,
        accepted_relationships: 1,
        unresolved_findings: 2,
        discoveries: [],
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await page
    .getByLabel("Research objective")
    .fill("Owned synthetic research-control test objective");
  await page
    .getByRole("button", { name: "Start research", exact: true })
    .click();
  await expect(page.locator(".research-summary")).toContainText("partial");
  await expect(page.locator(".research-summary")).toContainText(
    "4 model calls",
  );
  await expect(page.locator(".research-summary")).toContainText(
    "1 accepted links",
  );
});

test("real repeated research reaches the illustrated atlas (explicit opt-in)", async ({
  page,
  request,
}) => {
  test.skip(
    !process.env.CHRONICLES_REPEAT_JOB,
    "Opt-in real inference; requires the independent worker.",
  );
  test.setTimeout(960000);
  const original = await (
    await request.get(
      `http://127.0.0.1:8000/api/research/jobs/${process.env.CHRONICLES_REPEAT_JOB}`,
    )
  ).json();
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  await expect(
    page.getByText("Research archive", { exact: true }),
  ).toBeVisible();
  const screenshot = (name: string) =>
    page.screenshot({
      path: path.resolve("../../docs/phase-3-increment-4-" + name + ".png"),
      fullPage: true,
    });
  await screenshot("generated-spine");
  await page.getByRole("button", { name: /Open story moment 1:/ }).click();
  await screenshot("selected-event");
  const chars = page.getByRole("button", { name: /Characters [1-9]/ });
  if (await chars.count()) {
    await chars.click();
    await screenshot("relationships");
  }
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await page.getByLabel("Research objective").fill(original.objective);
  await page.getByLabel("Research episode boundary").fill("1");
  await page
    .getByRole("button", { name: "Start research", exact: true })
    .click();
  await expect(page.locator(".research-summary")).toBeVisible();
  const jid = await page
    .locator(".research-summary")
    .getAttribute("data-job-id");
  await writeFile(
    path.resolve("../../.tmp/increment4-repeat-job-id.txt"),
    jid ?? "",
  );
  await page.reload();
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await expect(page.locator(".research-summary")).toHaveAttribute(
    "data-job-id",
    jid ?? "",
  );
  await expect(page.locator(".research-summary strong")).toHaveText(
    /completed|partial|failed|cancelled/,
    { timeout: 920000 },
  );
  await screenshot("research-summary");
  const summary = await (
    await request.get(`/api/atlas/research/jobs/${jid}/summary`)
  ).json();
  expect(summary.status).not.toBe("failed");
  expect(summary.model_calls).toBeLessThanOrEqual(48);
  await page
    .getByRole("button", { name: "Refresh story atlas", exact: true })
    .click();
  await page.getByRole("button", { name: "Close research" }).click();
  await expect(
    page.getByText("Research archive", { exact: true }),
  ).toBeVisible();
});
