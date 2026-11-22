import { test, expect } from "@playwright/test";

test("Canvas 2D renderer draws and resizes in this browser engine", async ({ page }) => {
  await page.addInitScript(() => {
    window.__canvas2dDrawCalls = 0;
    const originalFillRect = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function (...args) {
      window.__canvas2dDrawCalls += 1;
      return originalFillRect.apply(this, args);
    };
  });

  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/tests/visual-engine-browser/canvas2d.html");
  const canvas = page.getByRole("img", { name: "Canvas Aurora cross-browser preview" });
  await expect(canvas).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__canvas2dDrawCalls)).toBeGreaterThan(0);
  await expect.poll(() => canvas.evaluate((node) => node.width)).toBeGreaterThan(300);
  await expect.poll(() => canvas.evaluate((node) => node.height)).toBeGreaterThan(300);
  await expect(page.getByRole("status")).toBeHidden();

  const initialWidth = await canvas.evaluate((node) => node.width);
  await page.setViewportSize({ width: 900, height: 900 });
  await expect.poll(() => canvas.evaluate((node) => node.width)).not.toBe(initialWidth);
  expect(pageErrors).toEqual([]);
});
