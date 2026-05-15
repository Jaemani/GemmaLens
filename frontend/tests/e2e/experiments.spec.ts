import { expect, test } from "@playwright/test";

test("experiment dashboard exposes all A/B switches", async ({ page }) => {
  await page.goto("/experiments");

  await expect(page.getByRole("heading", { name: "Experiment dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "1. Dictionary save" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "2. Highlight labels" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "3. Result layout" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "4. Item detail" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "5. Review state" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "6. User fit" })).toBeVisible();

  await page.getByRole("button", { name: "B Reader" }).click();
  await page.getByRole("button", { name: "B Card" }).click();
  await expect(page.getByText("Mixed variant")).toBeVisible();
});

test("demo analysis reflects experiment switches", async ({ page }) => {
  await page.goto("/experiments");
  await page.getByRole("button", { name: "B Reader" }).click();
  await page.getByRole("button", { name: "B Reason" }).click();

  await page.goto("/analysis/demo");

  await expect(page.getByText("Demo mode uses fixed sample data")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Reading context" })).toBeVisible();
  await expect(page.getByText("B reason labels")).toBeVisible();
});
