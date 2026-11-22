import { useEffect, useRef, useState } from "react";
import { mountVisualRuntime } from "./runtime";
import { mountCanvas2DRuntime } from "./canvas2d-runtime";
import type { Canvas2DEffectFactory, VisualEffectFactory, VisualRenderer, VisualRuntimeOptions } from "./types";
interface VisualSurfaceProps { effect: VisualEffectFactory | Canvas2DEffectFactory; renderer?: VisualRenderer; className?: string; label?: string; options?: VisualRuntimeOptions; }
export function VisualSurface({ effect, renderer = "webgl2", className, label = "Animated visual", options }: VisualSurfaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [failure, setFailure] = useState<{ effect: typeof effect; message: string } | null>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    try {
      return renderer === "canvas2d"
        ? mountCanvas2DRuntime(canvas, effect as Canvas2DEffectFactory, options)
        : mountVisualRuntime(canvas, effect as VisualEffectFactory, options);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Visual preview could not start.";
      setFailure({ effect, message });
      console.error("[VisualSurface]", cause);
      return undefined;
    }
  }, [effect, options, renderer]);
  const error = failure?.effect === effect ? failure.message : null;
  return <div className="visual-surface-host"><canvas ref={canvasRef} className={className} role="img" aria-label={label} />{error && <div className="visual-surface-error" role="status">Preview unavailable: {error}</div>}</div>;
}
