import type { VisualEffectFactory, VisualRuntimeOptions } from "./types";

const DEFAULT_OPTIONS: Required<VisualRuntimeOptions> = {
  maxPixelRatio: 1.75,
  pauseWhenHidden: true,
  respectReducedMotion: true,
};

/**
 * First-party WebGL2 runtime. It owns canvas lifecycle and delegates drawing
 * to independent effects; it has no dependency on a third-party scene engine.
 */
export function mountVisualRuntime(
  canvas: HTMLCanvasElement,
  createEffect: VisualEffectFactory,
  options: VisualRuntimeOptions = {},
): () => void {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const gl = canvas.getContext("webgl2", {
    alpha: true,
    antialias: true,
    depth: false,
    stencil: false,
    powerPreference: "high-performance",
  });

  if (!gl) throw new Error("WebGL2 is unavailable in this browser.");

  let disposed = false;
  let frameId = 0;
  let effect: ReturnType<VisualEffectFactory> | null = null;
  let width = 1;
  let height = 1;
  let pixelRatio = 1;
  let previousTime = 0;
  const pointer = { x: 0.5, y: 0.5, active: false };
  const reducedMotion = config.respectReducedMotion
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : null;

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
    gl.viewport(0, 0, bufferWidth, bufferHeight);
    effect?.resize?.(width, height, pixelRatio);
  };

  const initializeEffect = () => {
    resize();
    effect = createEffect(gl, { width, height, pixelRatio });
    effect.resize?.(width, height, pixelRatio);
  };

  const render = (timestamp: number) => {
    if (disposed) return;
    if (config.pauseWhenHidden && document.visibilityState === "hidden") {
      frameId = requestAnimationFrame(render);
      return;
    }

    const time = timestamp / 1000;
    const delta = previousTime === 0 ? 0 : Math.min(time - previousTime, 0.05);
    previousTime = time;
    effect?.render({ gl, time, delta, width, height, pixelRatio, pointer });

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
  const onReducedMotionChange = () => {
    cancelAnimationFrame(frameId);
    previousTime = 0;
    frameId = requestAnimationFrame(render);
  };
  const onContextLost = (event: Event) => {
    event.preventDefault();
    cancelAnimationFrame(frameId);
  };
  const onContextRestored = () => {
    effect?.dispose?.();
    effect = null;
    initializeEffect();
    previousTime = 0;
    frameId = requestAnimationFrame(render);
  };

  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  canvas.addEventListener("pointermove", onPointerMove, { passive: true });
  canvas.addEventListener("pointerleave", onPointerLeave);
  canvas.addEventListener("webglcontextlost", onContextLost);
  canvas.addEventListener("webglcontextrestored", onContextRestored);
  document.addEventListener("visibilitychange", onVisibilityChange);
  reducedMotion?.addEventListener("change", onReducedMotionChange);

  try {
    initializeEffect();
    frameId = requestAnimationFrame(render);
  } catch (error) {
    observer.disconnect();
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerleave", onPointerLeave);
    canvas.removeEventListener("webglcontextlost", onContextLost);
    canvas.removeEventListener("webglcontextrestored", onContextRestored);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    reducedMotion?.removeEventListener("change", onReducedMotionChange);
    throw error;
  }

  return () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    observer.disconnect();
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerleave", onPointerLeave);
    canvas.removeEventListener("webglcontextlost", onContextLost);
    canvas.removeEventListener("webglcontextrestored", onContextRestored);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    reducedMotion?.removeEventListener("change", onReducedMotionChange);
    effect?.dispose?.();
    effect = null;
  };
}
