import { expect, test } from "@playwright/test";
import { mockAnalysis } from "./fixtures";

test("internal experiment route is not part of the learner app", async ({ page }) => {
  await page.goto("/experiments");

  await expect(page).toHaveURL(/\/guide$/);
  await expect(page.getByRole("heading", { name: "Experiment dashboard" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "How to use GemmaLens" })).toBeVisible();
});

test("real analysis pages do not expose experiment controls", async ({ page }) => {
  await page.route("**/documents/real-doc", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "real-doc",
        title: "Real document",
        source_type: "text",
        content: "You're not gonna get away with this.",
        has_original_file: false,
        created_at: new Date(0).toISOString()
      })
    })
  );
  await page.route("**/documents/real-doc/analysis", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...mockAnalysis, document_id: "real-doc" })
    })
  );

  await page.goto("/analysis/real-doc");

  await expect(page.getByText("A/B test panel")).toHaveCount(0);
  await expect(page.getByText("User-fit mode")).toHaveCount(0);
  await expect(page.getByText("spoken English")).toBeVisible();
});
