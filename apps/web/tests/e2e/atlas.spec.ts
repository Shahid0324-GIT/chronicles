import { expect, test } from "@playwright/test";
test("fits a narrow viewport and keeps keyboard selection on the same page", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(
    page.getByRole("complementary", { name: "Journey story" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore", exact: true }).click();
  const search = page.getByRole("combobox", { name: "Search the atlas" });
  await search.fill("Emilia");
  await search.press("Enter");
  await expect(
    page
      .getByRole("complementary", { name: "Story information" })
      .getByRole("heading", { name: "Emilia", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close story information" }).click();
  await expect(
    page.getByRole("complementary", { name: "Story information" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Interactive universe map" }),
  ).toBeFocused();
  await page
    .getByRole("region", { name: "Interactive universe map" })
    .press("ArrowRight");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(page).toHaveURL("http://127.0.0.1:3000/");
});
// Uses the real seeded local FastAPI/PostgreSQL service. No mock research or API responses.
test("explores a persisted universe without leaving the canvas", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("complementary", { name: "Journey story" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Interactive universe map" }),
  ).toBeVisible();
  await expect(page.locator(".graph-failure")).toHaveCount(0);
  await expect(
    page.getByTestId("sigma-canvas").locator("canvas").first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Explore Emilia", exact: true })
    .click();
  const panel = page.getByRole("complementary", { name: "Story information" });
  await expect(
    panel.getByRole("heading", { name: "Emilia", exact: true }),
  ).toBeVisible();
  await panel.getByRole("button", { name: "Subaru Natsuki" }).click();
  await expect(
    panel.getByRole("heading", { name: "Subaru Natsuki" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Minimize story information" })
    .click();
  await expect(
    page.getByRole("button", { name: "Expand story information" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Return to full map" }).click();
  await expect(panel).toHaveCount(0);
  await page.getByRole("button", { name: "Guided", exact: false }).click();
  await expect(
    page
      .getByRole("complementary", { name: "Journey story" })
      .getByRole("heading", { name: "A world without a welcome" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore", exact: true }).click();
  await page.getByRole("combobox", { name: "Search the atlas" }).fill("Puck");
  await page.getByRole("combobox", { name: "Search the atlas" }).press("Enter");
  await expect(
    panel.getByRole("heading", { name: "Puck", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL("http://127.0.0.1:3000/");
  expect(errors).toEqual([]);
});
test("handles missing artwork, continuity filters, empty layers and reduced motion", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/art/silver.svg", (route) => route.abort());
  await page.goto("/");
  await expect(
    page.getByRole("complementary", { name: "Journey story" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore", exact: true }).click();
  await page
    .getByRole("button", { name: "Explore Emilia", exact: true })
    .click();
  const panel = page.getByRole("complementary", { name: "Story information" });
  await expect(panel.locator("img")).toHaveAttribute(
    "src",
    "/art/uncharted.svg",
  );
  await page.getByRole("button", { name: "Return to full map" }).click();
  await page
    .getByRole("combobox", { name: "Active continuity" })
    .selectOption("all");
  for (const name of [
    "characters",
    "events",
    "locations",
    "lore",
    "factions",
    "objects",
    "story arcs",
    "mysteries",
  ])
    await page
      .getByRole("button", { name: "Show " + name, exact: true })
      .click();
  await expect(
    page.getByRole("heading", { name: "Nothing in this layer." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Show all layers" }).click();
  await expect(
    page.getByRole("button", { name: "Explore Emilia", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /YOUR UNIVERSE/ }).click();
  await page.getByRole("button", { name: /Currently exploring/ }).click();
  await expect(
    page.getByRole("button", { name: "Explore Emilia", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL("http://127.0.0.1:3000/");
});

for (const mobile of [false, true]) {
  test(`preserves the story through a lore detour (${mobile ? "mobile reduced motion" : "desktop"})`, async ({
    page,
  }) => {
    if (mobile) {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.emulateMedia({ reducedMotion: "reduce" });
    }
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("/");
    const story = page.getByRole("complementary", { name: "Journey story" });
    const lore = page.getByRole("complementary", { name: "Lore discovery" });
    await expect(
      story.getByRole("heading", { name: "A world without a welcome" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Previous story moment" }),
    ).toBeDisabled();
    await page.getByRole("button", { name: "Next story moment" }).click();
    await expect(
      story.getByRole("heading", { name: "A promise in an unfamiliar city" }),
    ).toBeVisible();
    if (mobile) {
      await expect
        .poll(async () => {
          const node = await page
            .getByRole("button", {
              name: "Explore Search for the stolen insignia",
              exact: true,
            })
            .boundingBox();
          const panel = await story.boundingBox();
          const map = await page
            .getByRole("region", { name: "Interactive universe map" })
            .boundingBox();
          return Boolean(
            node &&
            panel &&
            map &&
            node.y + node.height / 2 < panel.y &&
            node.y > map.y,
          );
        })
        .toBe(true);
    }
    await story.getByRole("button", { name: "Inspect Subaru Natsuki" }).click();
    const entity = page.getByRole("complementary", {
      name: "Story information",
    });
    await expect(
      entity.getByRole("heading", { name: "Subaru Natsuki" }),
    ).toBeVisible();
    await entity
      .getByRole("button", {
        name: "Investigate Return by Death",
        exact: false,
      })
      .click();
    await expect(
      lore.getByRole("heading", { name: "The impossible return" }),
    ).toBeVisible();
    await expect(
      lore.getByText("Established in the opening", { exact: true }).first(),
    ).toBeVisible();
    await lore
      .getByRole("button", {
        name: "Recognizing a repeated beginning",
        exact: false,
      })
      .click();
    await expect(
      lore.getByRole("heading", { name: "Recognizing a repeated beginning" }),
    ).toBeVisible();
    await lore
      .getByRole("button", {
        name: "A second chance is still a burden",
        exact: false,
      })
      .click();
    await expect(
      lore.getByRole("heading", { name: "A second chance is still a burden" }),
    ).toBeVisible();
    await expect(
      lore.getByText("Editorial interpretation", { exact: true }).first(),
    ).toBeVisible();
    await lore
      .getByRole("button", { name: "What causes the return?", exact: false })
      .click();
    await expect(
      lore.getByRole("heading", { name: "What causes the return?" }),
    ).toBeVisible();
    await expect(
      lore.getByText("Unresolved in this scope", { exact: true }).first(),
    ).toBeVisible();
    await page.getByRole("button", { name: "Return to journey" }).click();
    await expect(
      story.getByRole("heading", { name: "A promise in an unfamiliar city" }),
    ).toBeVisible();
    await expect(
      page.getByRole("progressbar", { name: "Journey progress" }),
    ).toHaveAttribute("value", "2");
    await page.getByRole("button", { name: "Next story moment" }).click();
    await expect(
      story.getByRole("heading", { name: "An ending that leads back" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Next story moment" }).click();
    await expect(
      story.getByRole("heading", { name: "Giving the impossible a name" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Next story moment" }),
    ).toBeDisabled();
    await page.getByRole("button", { name: "Previous story moment" }).click();
    await expect(
      story.getByRole("heading", { name: "An ending that leads back" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(page).toHaveURL("http://127.0.0.1:3000/");
    expect(errors).toEqual([]);
  });
}
