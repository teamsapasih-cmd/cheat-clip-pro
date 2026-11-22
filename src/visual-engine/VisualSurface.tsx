import { useEffect, useRef } from "react";
import { mountVisualRuntime } from "./runtime";
import type { VisualEffectFactory, VisualRuntimeOptions } from "./types";

interface VisualSurfaceProps {
  effect: VisualEffectFactory;
  className?: string;
  label?: string;
  options?: VisualRuntimeOptions;
}

export function VisualSurface({
  effect,
  className,
  label = "Animated visual",
  options,
}: VisualSurfaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      return mountVisualRuntime(canvas, effect, options);
    } catch (error) {
      console.error("[VisualSurface]", error);
      return undefined;
    }
  }, [effect, options]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      role="img"
      aria-label={label}
    />
  );
}
