import { expect, test } from "@playwright/test";
import { mockVideoApi } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await mockVideoApi(page);
});

test("video page parses subtitles and shows timestamped transcript", async ({ page }) => {
  await page.goto("/video");

  await expect(page.getByRole("heading", { name: "Video learning" })).toBeVisible();
  await page.getByRole("button", { name: "Parse subtitle" }).click();

  const firstLine = page.getByRole("button", { name: /You're not gonna get away with this/ });
  await expect(firstLine).toBeVisible();
  await expect(page.getByRole("button", { name: /I should have told you earlier/ })).toBeVisible();
  await expect(firstLine).toContainText("0:01");
});

test("video transcript can be sent into analysis flow", async ({ page }) => {
  await page.goto("/video");

  await page.getByRole("button", { name: "Parse subtitle" }).click();
  await page.getByRole("button", { name: "Analyze transcript" }).click();

  await expect(page).toHaveURL(/\/analysis\/video-doc/);
  await expect(page.getByText("spoken English")).toBeVisible();
  await expect(page.getByText("get away with this", { exact: true })).toBeVisible();
});

test("persona sample buttons switch subtitle content", async ({ page }) => {
  await page.goto("/video");

  await page.getByRole("button", { name: "Technical tutorial" }).click();
  await expect(page.locator("textarea")).toHaveValue(/idempotent preflight check/);

  await page.getByRole("button", { name: "Academic lecture" }).click();
  await expect(page.locator("textarea")).toHaveValue(/laboratory findings generalize/);
});
