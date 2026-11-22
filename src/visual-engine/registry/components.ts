import { createAmbientFlowEffect } from "../effects/AmbientFlow";
import type { VisualComponentDefinition } from "./types";

export const visualComponents: VisualComponentDefinition[] = [
  {
    id: "ambient-flow",
    name: "Ambient Flow",
    category: "Backgrounds",
    description: "Procedural gradient field with gentle motion and pointer response.",
    version: 1,
    tags: ["webgl", "procedural", "gradient", "ambient"],
    controls: [
      { type: "range", key: "motion", label: "Motion", min: 0, max: 1, step: 0.05, defaultValue: 0.55 },
      { type: "range", key: "intensity", label: "Intensity", min: 0.2, max: 1, step: 0.05, defaultValue: 0.8 },
      { type: "toggle", key: "pointerResponse", label: "Pointer response", defaultValue: true },
    ],
    presets: [
      { id: "soft", name: "Soft", description: "Slow movement and restrained contrast.", values: { motion: 0.25, intensity: 0.55, pointerResponse: false } },
      { id: "balanced", name: "Balanced", description: "The default ambient appearance.", values: { motion: 0.55, intensity: 0.8, pointerResponse: true } },
      { id: "dynamic", name: "Dynamic", description: "More movement and stronger color contrast.", values: { motion: 0.9, intensity: 1, pointerResponse: true } },
    ],
    createEffect: () => createAmbientFlowEffect,
  },
];

export function getVisualComponent(id: string): VisualComponentDefinition | undefined {
  return visualComponents.find((component) => component.id === id);
}
