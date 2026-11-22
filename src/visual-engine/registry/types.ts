import type { Canvas2DEffectFactory, VisualEffectFactory } from "../types";
export type VisualControl =
  | { type: "range"; key: string; label: string; min: number; max: number; step?: number; defaultValue: number; unit?: string }
  | { type: "color"; key: string; label: string; defaultValue: string }
  | { type: "toggle"; key: string; label: string; defaultValue: boolean }
  | { type: "select"; key: string; label: string; defaultValue: string; options: Array<{ label: string; value: string }> };
export interface VisualPreset { id: string; name: string; description: string; values: Record<string, string | number | boolean>; }
interface VisualComponentBase { id: string; name: string; category: string; description: string; version: number; tags: string[]; controls: VisualControl[]; presets: VisualPreset[]; }
export type VisualComponentDefinition =
  | (VisualComponentBase & { renderer: "webgl2"; createEffect: (values: Record<string, string | number | boolean>) => VisualEffectFactory })
  | (VisualComponentBase & { renderer: "canvas2d"; createEffect: (values: Record<string, string | number | boolean>) => Canvas2DEffectFactory });
export type VisualValues = Record<string, string | number | boolean>;
