import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual-engine-browser",
  fullyParallel: false,
  reporter: "list",
  timeout: 30000,
  expect: { timeout: 8000 },
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-desktop",
      testMatch: "**/visual-engine.spec.mjs",
      use: {
        browserName: "chromium",
        viewport: { width: 1365, height: 900 },
        launchOptions: {
          args: [
            "--enable-webgl",
            "--enable-unsafe-swiftshader",
            "--use-gl=angle",
            "--use-angle=swiftshader",
          ],
        },
      },
    },
    {
      name: "chromium-mobile",
      testMatch: "**/visual-engine.spec.mjs",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 2,
        launchOptions: {
          args: [
            "--enable-webgl",
            "--enable-unsafe-swiftshader",
            "--use-gl=angle",
            "--use-angle=swiftshader",
          ],
        },
      },
    },
    {
      name: "firefox-canvas2d",
      testMatch: "**/cross-browser.spec.mjs",
      use: {
        browserName: "firefox",
        viewport: { width: 1365, height: 900 },
      },
    },
    {
      name: "webkit-canvas2d",
      testMatch: "**/cross-browser.spec.mjs",
      use: {
        browserName: "webkit",
        viewport: { width: 1365, height: 900 },
      },
    },
  ],
  webServer: {
    command: "npm run dev-frontend -- --host 127.0.0.1",
    url: "http://127.0.0.1:5173/tests/visual-engine-browser/",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
