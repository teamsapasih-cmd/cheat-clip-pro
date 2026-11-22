import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/tests/visual-engine-browser/");
  await expect(page.getByRole("heading", { name: "Explore components" })).toBeVisible();
});

async function expectPreviewHealthy(page, accessibleName) {
  const canvas = page.getByRole("img", { name: accessibleName });
  await expect(canvas).toBeVisible();
  await expect.poll(() => canvas.evaluate((node) => node.width)).toBeGreaterThan(0);
  await expect.poll(() => canvas.evaluate((node) => node.height)).toBeGreaterThan(0);
  await expect(page.locator(".visual-control-message").filter({ hasText: "Preview unavailable" })).toHaveCount(0);
}

test("renders all three effects using their respective renderer", async ({ page }) => {
  await expect(page.getByRole("button", { name: /Ambient Flow/ })).toBeVisible();
  await expectPreviewHealthy(page, "Ambient Flow visual preview");

  await page.getByRole("button", { name: /Canvas Aurora/ }).click();
  await expectPreviewHealthy(page, "Canvas Aurora visual preview");

  await page.getByRole("button", { name: /Particle Field/ }).click();
  await expectPreviewHealthy(page, "Particle Field visual preview");
});

test("search and category filters narrow the component gallery", async ({ page }) => {
  await page.getByRole("searchbox", { name: "Search visual components" }).fill("particle");
  await expect(page.getByRole("button", { name: /Particle Field/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Ambient Flow/ })).toHaveCount(0);
  await page.getByRole("searchbox", { name: "Search visual components" }).fill("");
  await page.getByRole("button", { name: "Backgrounds", exact: true }).click();
  await expect(page.getByRole("button", { name: /Ambient Flow/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Canvas Aurora/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Particle Field/ })).toHaveCount(0);
});

test("controls, presets, reset and JSON import/export work", async ({ page }) => {
  await page.getByLabel("Preset").selectOption("dynamic");
  await expect(page.getByText("More movement and stronger color contrast.")).toBeVisible();

  const motion = page.locator('input[type="range"]').first();
  await motion.focus();
  await motion.press("ArrowLeft");
  await expect(page.getByLabel("Preset")).toHaveValue("custom");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("ambient-flow-config.json");

  const config = JSON.stringify({
    schemaVersion: 1,
    componentId: "ambient-flow",
    values: { motion: 0.2, intensity: 0.6, pointerResponse: false },
  });
  await page.locator('input[type="file"]').setInputFiles({
    name: "ambient-flow-config.json",
    mimeType: "application/json",
    buffer: Buffer.from(config),
  });
  await expect(page.locator(".visual-control-message")).toContainText("Configuration imported.");
  await expect(motion).toHaveValue("0.2");

  await page.locator('input[type="file"]').setInputFiles({
    name: "oversized-config.json",
    mimeType: "application/json",
    buffer: Buffer.alloc(65_537, 0x20),
  });
  await expect(page.locator(".visual-control-message")).toContainText("maximum 64 KB");

  await page.getByRole("button", { name: "Reset" }).click();
  await expect(page.locator(".visual-control-message")).toContainText("Controls reset to defaults.");
  await expect(motion).toHaveValue("0.55");
});

test("layout adapts at mobile width without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const layout = page.locator(".visual-gallery-layout");
  await expect(layout).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
    columns: getComputedStyle(document.querySelector(".visual-gallery-layout")).gridTemplateColumns,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
  expect(dimensions.columns.split(" ").length).toBe(1);
  await expectPreviewHealthy(page, "Ambient Flow visual preview");
});

test("canvas resizes with its preview container", async ({ page }) => {
  const canvas = page.getByRole("img", { name: "Ambient Flow visual preview" });
  const initial = await canvas.evaluate((node) => ({ width: node.width, height: node.height }));
  await page.setViewportSize({ width: 900, height: 900 });
  await expect.poll(() => canvas.evaluate((node) => node.width)).not.toBe(initial.width);
  const resized = await canvas.evaluate((node) => ({ width: node.width, height: node.height }));
  expect(resized.width).toBeGreaterThan(0);
  expect(resized.height).toBeGreaterThan(0);
  expect(resized.width !== initial.width || resized.height !== initial.height).toBeTruthy();
});


test("animation pauses in hidden tabs and resumes after visibility returns", async ({ page }) => {
  await page.addInitScript(() => {
    window.__visualDrawCalls = 0;
    const originalDrawArrays = WebGL2RenderingContext.prototype.drawArrays;
    WebGL2RenderingContext.prototype.drawArrays = function (...args) {
      window.__visualDrawCalls += 1;
      return originalDrawArrays.apply(this, args);
    };
    window.__testVisibilityState = "visible";
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => window.__testVisibilityState,
    });
  });
  await page.goto("/tests/visual-engine-browser/");
  await expect.poll(() => page.evaluate(() => window.__visualDrawCalls)).toBeGreaterThan(3);

  await page.evaluate(() => {
    window.__testVisibilityState = "hidden";
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await page.waitForTimeout(180);
  const pausedAt = await page.evaluate(() => window.__visualDrawCalls);
  await page.waitForTimeout(180);
  const stillPausedAt = await page.evaluate(() => window.__visualDrawCalls);
  expect(stillPausedAt).toBe(pausedAt);

  await page.evaluate(() => {
    window.__testVisibilityState = "visible";
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => page.evaluate(() => window.__visualDrawCalls)).toBeGreaterThan(pausedAt);
});

test("reduced-motion preference pauses animation and resumes when disabled", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    window.__visualDrawCalls = 0;
    const originalDrawArrays = WebGL2RenderingContext.prototype.drawArrays;
    WebGL2RenderingContext.prototype.drawArrays = function (...args) {
      window.__visualDrawCalls += 1;
      return originalDrawArrays.apply(this, args);
    };
  });
  await page.goto("/tests/visual-engine-browser/");
  await expect.poll(() => page.evaluate(() => window.__visualDrawCalls)).toBeGreaterThan(0);
  await page.waitForTimeout(180);
  const reducedCount = await page.evaluate(() => window.__visualDrawCalls);
  await page.waitForTimeout(180);
  expect(await page.evaluate(() => window.__visualDrawCalls)).toBe(reducedCount);

  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect.poll(() => page.evaluate(() => window.__visualDrawCalls)).toBeGreaterThan(reducedCount);
});

test("WebGL context loss and restoration reinitialize the visual effect", async ({ page }) => {
  await page.addInitScript(() => {
    window.__visualDrawCalls = 0;
    const originalDrawArrays = WebGL2RenderingContext.prototype.drawArrays;
    WebGL2RenderingContext.prototype.drawArrays = function (...args) {
      window.__visualDrawCalls += 1;
      return originalDrawArrays.apply(this, args);
    };
  });
  await page.goto("/tests/visual-engine-browser/");
  await expect.poll(() => page.evaluate(() => window.__visualDrawCalls)).toBeGreaterThan(2);
  const supported = await page.getByRole("img", { name: "Ambient Flow visual preview" }).evaluate((canvas) => {
    const gl = canvas.getContext("webgl2");
    const extension = gl?.getExtension("WEBGL_lose_context");
    if (!extension) return false;
    extension.loseContext();
    window.setTimeout(() => extension.restoreContext(), 150);
    return true;
  });
  test.skip(!supported, "WEBGL_lose_context is not available in this Chromium runtime.");
  const previousDrawCount = await page.evaluate(() => window.__visualDrawCalls);
  await expect.poll(() => page.evaluate(() => window.__visualDrawCalls), { timeout: 12000 }).toBeGreaterThan(previousDrawCount);
  await expect(page.locator(".visual-control-message").filter({ hasText: "Preview unavailable" })).toHaveCount(0);
});

test("switching renderers disposes the previous animation loop", async ({ page }) => {
  await page.addInitScript(() => {
    window.__webglDrawCalls = 0;
    window.__canvas2dDrawCalls = 0;
    const originalWebGLDraw = WebGL2RenderingContext.prototype.drawArrays;
    WebGL2RenderingContext.prototype.drawArrays = function (...args) {
      window.__webglDrawCalls += 1;
      return originalWebGLDraw.apply(this, args);
    };
    const originalCanvasDraw = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function (...args) {
      window.__canvas2dDrawCalls += 1;
      return originalCanvasDraw.apply(this, args);
    };
  });

  await page.goto("/tests/visual-engine-browser/");
  await expect.poll(() => page.evaluate(() => window.__webglDrawCalls)).toBeGreaterThan(3);

  await page.getByRole("button", { name: /Canvas Aurora/ }).click();
  await expect.poll(() => page.evaluate(() => window.__canvas2dDrawCalls)).toBeGreaterThan(3);
  const webglAfterSwitch = await page.evaluate(() => window.__webglDrawCalls);
  await page.waitForTimeout(180);
  expect(await page.evaluate(() => window.__webglDrawCalls)).toBe(webglAfterSwitch);

  await page.getByRole("button", { name: /Particle Field/ }).click();
  await expect.poll(() => page.evaluate(() => window.__webglDrawCalls)).toBeGreaterThan(webglAfterSwitch);
  const canvasAfterSwitch = await page.evaluate(() => window.__canvas2dDrawCalls);
  await page.waitForTimeout(180);
  expect(await page.evaluate(() => window.__canvas2dDrawCalls)).toBe(canvasAfterSwitch);
});

