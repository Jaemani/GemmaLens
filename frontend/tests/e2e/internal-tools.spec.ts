import { expect, test } from "@playwright/test";

test("internal experiment route is not part of the learner app", async ({ page }) => {
  await page.goto("/experiments");

  await expect(page.getByRole("heading", { name: "Experiment dashboard" })).toHaveCount(0);
  await expect(page.getByText(/404|not found/i)).toBeVisible();
});

test("real analysis pages do not expose experiment controls", async ({ page }) => {
  await page.goto("/analysis/95a095cf-71fb-42ec-9b76-934c32ce86ca");

  await expect(page.getByText("A/B test panel")).toHaveCount(0);
  await expect(page.getByText("User-fit mode")).toHaveCount(0);
  await expect(page.getByText("Complete paper learning guide")).toBeVisible();
});
