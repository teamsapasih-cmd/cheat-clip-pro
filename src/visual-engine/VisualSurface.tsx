import { useEffect, useRef } from "react";
import { mountVisualRuntime } from "./runtime";
import { mountCanvas2DRuntime } from "./canvas2d-runtime";
import type { Canvas2DEffectFactory, VisualEffectFactory, VisualRenderer, VisualRuntimeOptions } from "./types";

interface VisualSurfaceProps {
  effect: VisualEffectFactory | Canvas2DEffectFactory;
  renderer?: VisualRenderer;
  className?: string;
  label?: string;
  options?: VisualRuntimeOptions;
}

export function VisualSurface({ effect, renderer = "webgl2", className, label = "Animated visual", options }: VisualSurfaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const errorNode = errorRef.current;
    if (!canvas) return;

    const showError = (cause: unknown) => {
      const message = cause instanceof Error ? cause.message : "Visual preview could not continue.";
      if (errorNode) {
        errorNode.textContent = "Preview unavailable: " + message;
        errorNode.hidden = false;
      }
      console.error("[VisualSurface]", cause);
    };

    if (errorNode) {
      errorNode.hidden = true;
      errorNode.textContent = "";
    }

    const runtimeOptions = { ...options, onError: showError };
    try {
      return renderer === "canvas2d"
        ? mountCanvas2DRuntime(canvas, effect as Canvas2DEffectFactory, runtimeOptions)
        : mountVisualRuntime(canvas, effect as VisualEffectFactory, runtimeOptions);
    } catch (cause) {
      showError(cause);
      return undefined;
    }
  }, [effect, options, renderer]);

  return (
    <div className="visual-surface-host">
      <canvas ref={canvasRef} className={className} role="img" aria-label={label} />
      <div ref={errorRef} className="visual-surface-error" role="status" hidden />
    </div>
  );
}
