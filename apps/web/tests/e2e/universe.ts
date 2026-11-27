import { expect, type Page } from "@playwright/test";

/** Select explicitly: adding a universe must not change what a regression exercises. */
export async function openUniverse(
  page: Page,
  title: RegExp,
  continuity?: string,
) {
  await page.goto("/atlas");
  await page.locator(".world-switch").click();
  await page
    .locator("#universe-menu button")
    .filter({ has: page.locator("strong", { hasText: title }) })
    .click();
  if (continuity) {
    await page.getByLabel("Active continuity").selectOption(continuity);
    await expect(page.getByLabel("Active continuity")).toHaveValue(continuity);
  }
}
