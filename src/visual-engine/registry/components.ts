import { createAmbientFlowEffect } from "../effects/AmbientFlow";
import { createCanvasAuroraEffect } from "../effects/CanvasAurora";
import { createParticleFieldEffect } from "../effects/ParticleField";
import type { VisualComponentDefinition } from "./types";
export const visualComponents: VisualComponentDefinition[] = [
  {
    id: "ambient-flow", name: "Ambient Flow", category: "Backgrounds", description: "Procedural gradient field with gentle motion and pointer response.", version: 1, renderer: "webgl2",
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
    createEffect: (values) => createAmbientFlowEffect({ motion: typeof values.motion === "number" ? values.motion : 0.55, intensity: typeof values.intensity === "number" ? values.intensity : 0.8, pointerResponse: typeof values.pointerResponse === "boolean" ? values.pointerResponse : true }),
  },
  {
    id: "particle-field", name: "Particle Field", category: "Particles",
    description: "A procedural field of softly drifting points with layered depth.", version: 1, renderer: "webgl2",
    tags: ["webgl", "particles", "procedural", "motion"],
    controls: [
      { type: "range", key: "motion", label: "Motion", min: 0, max: 1, step: 0.05, defaultValue: 0.5 },
      { type: "range", key: "intensity", label: "Intensity", min: 0.1, max: 1, step: 0.05, defaultValue: 0.8 },
      { type: "range", key: "size", label: "Particle size", min: 0.5, max: 2, step: 0.1, defaultValue: 1 },
    ],
    presets: [
      { id: "calm", name: "Calm", description: "Slow and subtle particle motion.", values: { motion: 0.2, intensity: 0.55, size: 0.8 } },
      { id: "active", name: "Active", description: "Balanced movement and particle density.", values: { motion: 0.5, intensity: 0.8, size: 1 } },
      { id: "vivid", name: "Vivid", description: "Faster motion with brighter, larger points.", values: { motion: 0.9, intensity: 1, size: 1.5 } },
    ],
    createEffect: (values) => createParticleFieldEffect({
      motion: typeof values.motion === "number" ? values.motion : 0.5,
      intensity: typeof values.intensity === "number" ? values.intensity : 0.8,
      size: typeof values.size === "number" ? values.size : 1,
    }),
  },
  {
    id: "canvas-aurora", name: "Canvas Aurora", category: "Backgrounds", description: "Soft layered color fields rendered with the native Canvas 2D API.", version: 1, renderer: "canvas2d",
    tags: ["canvas2d", "aurora", "gradient", "lightweight"], controls: [
      { type: "range", key: "motion", label: "Motion", min: 0, max: 1, step: 0.05, defaultValue: 0.55 },
      { type: "range", key: "intensity", label: "Intensity", min: 0.2, max: 1, step: 0.05, defaultValue: 0.8 },
      { type: "toggle", key: "pointerResponse", label: "Pointer response", defaultValue: true },
    ],
    presets: [
      { id: "mist", name: "Mist", description: "Soft and slow ambient color movement.", values: { motion: 0.2, intensity: 0.55, pointerResponse: false } },
      { id: "aurora", name: "Aurora", description: "Balanced layered light and movement.", values: { motion: 0.55, intensity: 0.8, pointerResponse: true } },
      { id: "radiant", name: "Radiant", description: "Brighter color fields with more movement.", values: { motion: 0.9, intensity: 1, pointerResponse: true } },
    ],
    createEffect: (values) => createCanvasAuroraEffect({
      motion: typeof values.motion === "number" ? values.motion : 0.55,
      intensity: typeof values.intensity === "number" ? values.intensity : 0.8,
      pointerResponse: typeof values.pointerResponse === "boolean" ? values.pointerResponse : true,
    }),
  },
];
export function getVisualComponent(id: string): VisualComponentDefinition | undefined { return visualComponents.find((component) => component.id === id); }
