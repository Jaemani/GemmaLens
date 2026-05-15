import { expect, test } from "@playwright/test";
import { mockVideoApi } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await mockVideoApi(page);
});

test("video page parses subtitles and shows timestamped transcript", async ({ page }) => {
  await page.goto("/video");

  await expect(page.getByRole("heading", { name: "Video learning" })).toBeVisible();
  await page.locator("textarea").fill(`1
00:00:01,000 --> 00:00:03,500
You're not gonna get away with this.

2
00:00:04,000 --> 00:00:06,200
I should have told you earlier.
`);
  await page.getByRole("button", { name: "Parse subtitle" }).click();

  const firstLine = page.getByRole("button", { name: /You're not gonna get away with this/ });
  await expect(firstLine).toBeVisible();
  await expect(page.getByRole("button", { name: /I should have told you earlier/ })).toBeVisible();
  await expect(firstLine).toContainText("0:01");
});

test("video transcript can be sent into analysis flow", async ({ page }) => {
  await page.goto("/video");

  await page.locator("textarea").fill(`1
00:00:01,000 --> 00:00:03,500
You're not gonna get away with this.
`);
  await page.getByRole("button", { name: "Parse subtitle" }).click();
  await page.getByRole("button", { name: "Analyze transcript" }).click();

  await expect(page).toHaveURL(/\/analysis\/video-doc/);
  await expect(page.getByText("spoken English")).toBeVisible();
  await expect(page.getByText("get away with this", { exact: true })).toBeVisible();
});

test("youtube transcript fetch replaces empty transcript state", async ({ page }) => {
  await page.goto("/video");

  await expect(page.locator("textarea")).toHaveValue("");
  await page.getByPlaceholder("YouTube URL").fill("https://youtu.be/dQw4w9WgXcQ");
  await page.getByRole("button", { name: "Fetch transcript" }).click();

  await expect(page.getByRole("button", { name: /You're not gonna get away with this/ })).toBeVisible();
  await expect(page.locator("textarea")).toHaveValue("");
});
