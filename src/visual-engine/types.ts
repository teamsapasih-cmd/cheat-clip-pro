export interface VisualFrame { gl: WebGL2RenderingContext; time: number; delta: number; width: number; height: number; pixelRatio: number; pointer: { x: number; y: number; active: boolean }; }
export interface VisualEffectInstance { render(frame: VisualFrame): void; resize?(width: number, height: number, pixelRatio: number): void; dispose?(): void; }
export type VisualEffectFactory = (gl: WebGL2RenderingContext, size: { width: number; height: number; pixelRatio: number }) => VisualEffectInstance;
export interface Canvas2DFrame { ctx: CanvasRenderingContext2D; time: number; delta: number; width: number; height: number; pixelRatio: number; pointer: { x: number; y: number; active: boolean }; }
export interface Canvas2DEffectInstance { render(frame: Canvas2DFrame): void; resize?(width: number, height: number, pixelRatio: number): void; dispose?(): void; }
export type Canvas2DEffectFactory = (ctx: CanvasRenderingContext2D, size: { width: number; height: number; pixelRatio: number }) => Canvas2DEffectInstance;
export type VisualRenderer = "webgl2" | "canvas2d";
export interface VisualRuntimeOptions { maxPixelRatio?: number; pauseWhenHidden?: boolean; respectReducedMotion?: boolean; }
