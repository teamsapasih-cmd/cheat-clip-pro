# Independent Visual Engine

## Clean-room boundary

This implementation is authored independently for Clip Intelligence Studio. It does not import ThreeUI, Three.js, ThreeUI source files, ThreeUI imagery, remote ThreeUI previews, or bundled ThreeUI fonts. ThreeUI is used only as a high-level product reference for the kinds of capabilities a visual component system can offer.

## First-party architecture

- Runtime: owns WebGL2 context lifecycle, resize handling, device-pixel-ratio limits, animation scheduling, visibility pausing, reduced-motion behavior, pointer input, context-loss recovery, and cleanup.
- Shader utilities: compile and link independently authored GLSL programs with explicit error reporting.
- Effect contract: each visual is an isolated factory returning render, resize, and dispose hooks.
- React surface: a small host component connects a visual effect to the application without coupling it to the clip-processing pipeline.
- Future registry: metadata, categories, controls, presets, and variants are stored separately from renderers.

## Planned capabilities

1. Procedural 2D and 3D visuals built with browser-native Canvas2D and WebGL2.
2. Parameter controls with validated defaults and safe ranges.
3. Reusable presets and variants implemented as first-party configurations.
4. Theme-aware palettes, responsive sizing, and pointer interaction.
5. Reduced-motion support, visibility pausing, and graceful fallback for unsupported WebGL2 devices.
6. Lazy loading and per-effect resource cleanup.

## Non-goals

- Do not install the ThreeUI package or copy ThreeUI implementation code.
- Do not redistribute ThreeUI-authored images, previews, fonts, or other assets.
- Do not change video processing, storage, temporary-file cleanup, Supabase, or retention behavior as part of this visual-engine work.

## Integration policy

The engine remains isolated until a specific visual component is ready and tested. It must not alter the existing Clip Intelligence Studio workflow or render pipeline.
