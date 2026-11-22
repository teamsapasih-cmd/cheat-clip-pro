export interface VisualFrame {
  gl: WebGL2RenderingContext;
  time: number;
  delta: number;
  width: number;
  height: number;
  pixelRatio: number;
  pointer: { x: number; y: number; active: boolean };
}

export interface VisualEffectInstance {
  render(frame: VisualFrame): void;
  resize?(width: number, height: number, pixelRatio: number): void;
  dispose?(): void;
}

export type VisualEffectFactory = (
  gl: WebGL2RenderingContext,
  size: { width: number; height: number; pixelRatio: number },
) => VisualEffectInstance;

export interface VisualRuntimeOptions {
  maxPixelRatio?: number;
  pauseWhenHidden?: boolean;
  respectReducedMotion?: boolean;
}
