import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001";
const port = new URL(baseURL).port || "3001";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL,
    trace: "retain-on-failure"
  },
  webServer: {
    command: `npm run dev -- --hostname 127.0.0.1 --port ${port}`,
    url: baseURL,
    reuseExistingServer: false,
    env: {
      BACKEND_INTERNAL_URL: "http://127.0.0.1:9",
      NEXT_PUBLIC_API_BASE_URL: "",
      NEXT_PUBLIC_GEMMALENS_API_KEY: "",
      NEXT_PUBLIC_DIRECT_UPLOAD_BASE_URL: "",
      GEMMALENS_API_KEY: "",
      NEXT_TELEMETRY_DISABLED: "1",
    },
    timeout: 120_000
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
