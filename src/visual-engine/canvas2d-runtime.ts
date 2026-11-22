import { observeCanvasResize } from "./observe-resize";
import type { Canvas2DEffectFactory, VisualRuntimeOptions } from "./types";

const DEFAULT_OPTIONS: Required<Omit<VisualRuntimeOptions, "onError">> = {
  maxPixelRatio: 1.75,
  pauseWhenHidden: true,
  respectReducedMotion: true,
};

export function mountCanvas2DRuntime(
  canvas: HTMLCanvasElement,
  createEffect: Canvas2DEffectFactory,
  options: VisualRuntimeOptions = {},
): () => void {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
  if (!ctx) throw new Error("Canvas 2D is unavailable in this browser.");

  let disposed = false;
  let frameId = 0;
  let width = 1;
  let height = 1;
  let pixelRatio = 1;
  let previousTime = 0;
  let effect: ReturnType<Canvas2DEffectFactory> | null = null;
  const pointer = { x: 0.5, y: 0.5, active: false };
  const reducedMotion = config.respectReducedMotion
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : null;

  const reportError = (error: unknown) => {
    try {
      config.onError?.(error);
    } catch (callbackError) {
      console.error("[Canvas2DRuntime] Error callback failed.", callbackError);
    }
  };

  const resize = () => {
    if (disposed) return;
    const rect = canvas.getBoundingClientRect();
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    pixelRatio = Math.min(window.devicePixelRatio || 1, config.maxPixelRatio);
    const bufferWidth = Math.max(1, Math.round(width * pixelRatio));
    const bufferHeight = Math.max(1, Math.round(height * pixelRatio));
    if (canvas.width !== bufferWidth || canvas.height !== bufferHeight) {
      canvas.width = bufferWidth;
      canvas.height = bufferHeight;
    }
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    effect?.resize?.(width, height, pixelRatio);
  };

  const render = (timestamp: number) => {
    if (disposed || (config.pauseWhenHidden && document.visibilityState === "hidden")) return;
    const time = timestamp / 1000;
    const delta = previousTime === 0 ? 0 : Math.min(time - previousTime, 0.05);
    previousTime = time;
    try {
      effect?.render({ ctx, time, delta, width, height, pixelRatio, pointer });
    } catch (error) {
      cancelAnimationFrame(frameId);
      reportError(error);
      return;
    }
    if (!reducedMotion?.matches) frameId = requestAnimationFrame(render);
  };

  const onPointerMove = (event: PointerEvent) => {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    pointer.x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    pointer.y = 1 - Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
    pointer.active = true;
  };
  const onPointerLeave = () => { pointer.active = false; };
  const onVisibilityChange = () => {
    if (document.visibilityState === "visible") {
      previousTime = 0;
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(render);
    }
  };
  const onMotionChange = () => {
    cancelAnimationFrame(frameId);
    previousTime = 0;
    frameId = requestAnimationFrame(render);
  };

  const stopObservingResize = observeCanvasResize(canvas, resize);
  canvas.addEventListener("pointermove", onPointerMove, { passive: true });
  canvas.addEventListener("pointerleave", onPointerLeave);
  document.addEventListener("visibilitychange", onVisibilityChange);
  reducedMotion?.addEventListener("change", onMotionChange);

  try {
    resize();
    effect = createEffect(ctx, { width, height, pixelRatio });
    effect.resize?.(width, height, pixelRatio);
    frameId = requestAnimationFrame(render);
  } catch (error) {
    stopObservingResize();
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerleave", onPointerLeave);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    reducedMotion?.removeEventListener("change", onMotionChange);
    effect?.dispose?.();
    throw error;
  }

  return () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    stopObservingResize();
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerleave", onPointerLeave);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    reducedMotion?.removeEventListener("change", onMotionChange);
    effect?.dispose?.();
    effect = null;
  };
}
