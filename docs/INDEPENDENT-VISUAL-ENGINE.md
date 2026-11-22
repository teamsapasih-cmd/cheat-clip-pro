# Independent Visual Engine

## Clean-room boundary

This implementation is authored independently for Clip Intelligence Studio. It does not import ThreeUI, Three.js, ThreeUI source files, ThreeUI imagery, remote ThreeUI previews, or bundled ThreeUI fonts. ThreeUI is used only as a high-level product reference for the kinds of capabilities a visual component system can offer.

## First-party architecture

- **WebGL2 runtime:** owns GPU context lifecycle, resize handling, device-pixel-ratio limits, animation scheduling, visibility pausing, reduced-motion behavior, pointer input, context-loss recovery, and cleanup.
- **Canvas 2D runtime:** provides a lighter browser-native rendering path with matching sizing, animation, pointer, visibility, and cleanup behavior.
- **Shader utilities:** compile and link independently authored GLSL programs with explicit error reporting and cleanup.
- **Effect contracts:** each visual is an isolated renderer-specific factory returning render, resize, and dispose hooks.
- **Registry:** renderer choice, metadata, categories, controls, presets, and tags are separate from the rendering surface.
- **React workbench:** a small host connects visual effects to controls without coupling them to the clip-processing pipeline.

## Current components

1. **Ambient Flow** — procedural WebGL2 gradient field with motion, intensity, and pointer-response controls plus three presets.
2. **Canvas Aurora** — layered Canvas 2D color field with pointer-responsive movement.

## Planned capabilities

1. Expand the original component library with particles, grids, orbits, typography, and other visual families.
2. Add validated color, range, toggle, and select controls where each effect needs them.
3. Add exportable/importable configuration presets and extend the searchable category gallery.
4. Add theme-aware palettes, responsive sizing, and accessibility checks.
5. Add browser-level rendering, context-loss, reduced-motion, and performance tests.
6. Add lazy loading and resource budgets before production integration.

## Non-goals

- Do not install the ThreeUI package or copy ThreeUI implementation code.
- Do not redistribute ThreeUI-authored images, previews, fonts, or other assets.
- Do not change video processing, storage, temporary-file cleanup, Supabase, or retention behavior as part of this visual-engine work.

## Integration policy

The engine remains isolated from the existing Clip Intelligence Studio workflow and render pipeline. The workbench is exported as a module and is not mounted into the production app. No Railway deployment is made until build, lint, and browser/GPU checks pass.
