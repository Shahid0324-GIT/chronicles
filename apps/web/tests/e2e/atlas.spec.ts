import { expect, test } from "@playwright/test";
// Legacy UI cases explicitly exercise the curated fallback; live integration is separate.
test.beforeEach(async ({ page }) => {
  await page.route("**/api/atlas/universes/*/narrative?*", (route) =>
    route.fulfill({ status: 503, json: { error: "Owned fallback test" } }),
  );
});
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
  await page.getByRole("button", { name: "Re:Zero", exact: true }).click();
  await page.getByRole("button", { name: /Currently exploring/ }).click();
  await expect(
    page.getByRole("navigation", { name: "Story milestones" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore", exact: true }).click();
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
    await page
      .getByRole("group", { name: "Explore event branches" })
      .getByRole("button", { name: /Characters/ })
      .click();
    await page
      .getByRole("region", { name: "Characters branch" })
      .getByRole("button", { name: "Inspect Subaru Natsuki" })
      .click();
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
    await page
      .getByRole("button", {
        name: "Recognizing a repeated beginning",
        exact: false,
      })
      .click();
    await expect(
      lore.getByRole("heading", { name: "Recognizing a repeated beginning" }),
    ).toBeVisible();
    await page
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
    await page
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
      page.getByRole("progressbar", {
        name: "Journey progress",
        includeHidden: true,
      }),
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

test("opens illustrated milestones, reveals scoped branches and keeps the story visible", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  const spine = page.getByRole("navigation", { name: "Story milestones" });
  await expect(spine.getByRole("button")).toHaveCount(4);
  await expect(page.getByTestId("sigma-canvas")).toHaveCount(0);
  await page
    .getByRole("checkbox", { name: "Preview upcoming details" })
    .uncheck();
  await expect(
    spine.getByRole("button", { name: "Continue to moment 3", exact: true }),
  ).toBeVisible();
  await expect(
    spine.getByRole("button", { name: /An ending that leads back/ }),
  ).toHaveCount(0);
  await page
    .getByRole("checkbox", { name: "Preview upcoming details" })
    .check();
  await spine
    .getByRole("button", {
      name: "Open story moment 2: A promise in an unfamiliar city",
      exact: true,
    })
    .click();
  await expect(spine.locator('[aria-current="step"]')).toHaveAccessibleName(
    "Open story moment 2: A promise in an unfamiliar city",
  );
  const causes = page.getByRole("region", { name: "Causes", exact: true });
  const consequences = page.getByRole("region", {
    name: "Consequences",
    exact: true,
  });
  await expect(
    causes.getByText(
      "No explicit causal relationship is recorded for this moment.",
    ),
  ).toBeVisible();
  await expect(
    consequences.getByText("Story sequence · not a causal claim"),
  ).toBeVisible();
  const branches = page.getByRole("group", { name: "Explore event branches" });
  await branches.getByRole("button", { name: /Characters/ }).click();
  await expect(
    page.getByRole("region", { name: "Characters branch" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Collapse branch" }).click();
  await expect(
    page.getByRole("region", { name: "Characters branch" }),
  ).toHaveCount(0);
  await branches.getByRole("button", { name: /Lore/ }).click();
  await page
    .getByRole("button", { name: "Investigate Return by Death" })
    .click();
  await expect(
    page.getByRole("complementary", { name: "Lore discovery" }),
  ).toBeVisible();
  await expect(spine).toBeInViewport();
  await expect(
    page.getByRole("region", { name: "Lore branch" }),
  ).toBeInViewport({ ratio: 1 });
  await page
    .getByRole("complementary", { name: "Lore discovery" })
    .getByRole("button", { name: "Sources & scope" })
    .click();
  const notes = page.getByRole("complementary", { name: "Source notes" });
  await expect(
    notes.getByRole("link", { name: /Official anime story guide/ }),
  ).toHaveAttribute("href", "https://re-zero-anime.jp/tv/story/tv1r.html");
  await page
    .getByRole("button", { name: "Close source notes" })
    .press("Escape");
  await expect(notes).toHaveCount(0);
  await page.getByRole("button", { name: "Return to journey" }).click();
  await expect(spine.locator('[aria-current="step"]')).toHaveAccessibleName(
    /Open story moment 2/,
  );
  await expect(page.getByRole("region", { name: "Lore branch" })).toHaveCount(
    0,
  );
  await consequences
    .getByRole("button", { name: "An ending that leads back" })
    .click();
  await expect(spine.locator('[aria-current="step"]')).toHaveAccessibleName(
    /Open story moment 3/,
  );
  await causes
    .getByRole("button", { name: "A promise in an unfamiliar city" })
    .click();
  await expect(spine.locator('[aria-current="step"]')).toHaveAccessibleName(
    /Open story moment 2/,
  );
  await expect(page).toHaveURL("http://127.0.0.1:3000/");
});

for (const reduced of [false, true]) {
  test(`handles rapid milestone changes and keyboard navigation (${reduced ? "reduced" : "normal"} motion)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.emulateMedia({
      reducedMotion: reduced ? "reduce" : "no-preference",
    });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("/");
    const spine = page.getByRole("navigation", { name: "Story milestones" });
    await page.getByRole("button", { name: "Lore", exact: true }).click();
    await expect(
      page
        .getByRole("region", { name: "Lore branch" })
        .getByText(/JOURNEY BOOKMARK/),
    ).toBeVisible();
    await page.getByRole("button", { name: "Return to journey" }).click();
    for (const index of [2, 4, 1, 3, 2])
      await spine
        .getByRole("button", {
          name: new RegExp("^Open story moment " + index + ":"),
        })
        .click();
    await spine.locator('[aria-current="step"]').press("ArrowRight");
    await expect(spine.locator('[aria-current="step"]')).toHaveAccessibleName(
      /Open story moment 3/,
    );
    await expect(
      page.getByRole("complementary", { name: "Journey story" }),
    ).toHaveCSS("opacity", "1");
    await spine.locator('[aria-current="step"]').press("Home");
    await expect(spine.locator('[aria-current="step"]')).toHaveAccessibleName(
      /Open story moment 1/,
    );
    expect(errors).toEqual([]);
  });
}
