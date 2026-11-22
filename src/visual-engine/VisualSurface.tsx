import { useEffect, useRef, useState } from "react";
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    setError(null);
    try {
      return mountVisualRuntime(canvas, effect, options);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Visual preview could not start.";
      setError(message);
      console.error("[VisualSurface]", cause);
      return undefined;
    }
  }, [effect, options]);

  return (
    <div className="visual-surface-host">
      <canvas
        ref={canvasRef}
        className={className}
        role="img"
        aria-label={label}
      />
      {error && (
        <div className="visual-surface-error" role="status">
          Preview unavailable: {error}
        </div>
      )}
    </div>
  );
}
