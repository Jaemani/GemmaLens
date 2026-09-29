import { test, expect } from "./fixtures";

test("portable screenshots use isolated data and configured origin", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/dictionary");
  await expect(page.getByRole("heading", { name: /library/i }).first()).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("library.png") });
  await page.goto("/guide");
  await expect(page.getByRole("heading", { name: "Guide", exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("guide.png") });
});
