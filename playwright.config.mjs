import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual-engine-browser",
  testMatch: "**/*.spec.mjs",
  fullyParallel: false,
  reporter: "list",
  timeout: 30000,
  expect: { timeout: 8000 },
  use: {
    baseURL: "http://127.0.0.1:5173",
    browserName: "chromium",
    launchOptions: {
      args: [
        "--enable-webgl",
        "--enable-unsafe-swiftshader",
        "--use-gl=angle",
        "--use-angle=swiftshader",
      ],
    },
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium-desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1365, height: 900 } } },
    { name: "chromium-mobile", use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" } },
  ],
  webServer: {
    command: "npm run dev-frontend -- --host 127.0.0.1",
    url: "http://127.0.0.1:5173/tests/visual-engine-browser/",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
