# Independent Visual Engine

## Clean-room boundary

This implementation is authored independently for Clip Intelligence Studio. It does not import ThreeUI, Three.js, ThreeUI source files, ThreeUI imagery, remote ThreeUI previews, or bundled ThreeUI fonts. ThreeUI is used only as a high-level product reference for the kinds of capabilities a visual component system can offer.

## First-party architecture

- **WebGL2 runtime:** owns GPU context lifecycle, resize handling, device-pixel-ratio limits, animation scheduling, visibility pausing, reduced-motion behavior, pointer input, context-loss recovery, and cleanup.
- **Canvas 2D runtime:** provides a lighter browser-native rendering path with matching sizing, animation, pointer, visibility, and cleanup behavior.
- **Resize compatibility:** uses `ResizeObserver` when available and falls back to window resize events on older environments.
- **Shader utilities:** compile and link independently authored GLSL programs with explicit error reporting and cleanup.
- **Effect contracts:** each visual is an isolated renderer-specific factory returning render, resize, and dispose hooks.
- **Registry:** renderer choice, metadata, categories, controls, presets, and tags are separate from the rendering surface.
- **React workbench:** a small host connects visual effects to controls without coupling them to the clip-processing pipeline; runtime failures are surfaced through an accessible status message.

## Implemented components

1. **Ambient Flow** — procedural WebGL2 gradient field with motion, intensity, and pointer-response controls plus three presets.
2. **Canvas Aurora** — layered Canvas 2D color field with motion, intensity, and pointer-response controls plus three presets.
3. **Particle Field** — procedural WebGL2 particle field with motion, intensity, and size controls plus three presets.
4. **Portable configurations** — versioned JSON export/import with component validation, 64 KB input limit, and safe defaults. Users can download/import a local JSON file or reset controls; configurations are not persisted to browser storage or media storage.
5. **Interactive gallery/workbench** — searchable and category-filtered component gallery, live preview, responsive layout, and renderer-specific fallback.

## Next development capabilities

These are future enhancements, not part of the current implementation:
1. Expand the original component library with grids, orbits, typography, and additional visual families.
2. Add theme-aware palettes and additional accessibility checks.
3. Add lazy loading and explicit GPU/resource budgets before production integration.
4. Add optional reusable project-level presets only after a separate persistence/security design review.

## Non-goals

- Do not install the ThreeUI package or copy ThreeUI implementation code.
- Do not redistribute ThreeUI-authored images, previews, fonts, or other assets.
- Do not change video processing, storage, temporary-file cleanup, Supabase, or retention behavior as part of this visual-engine work.

## Integration policy

The engine remains isolated from the existing Clip Intelligence Studio workflow and render pipeline. The workbench is exported as a module and is not mounted into the production app. No Railway deployment is made until build, lint, browser checks, and real-device GPU validation pass.

## Automated browser validation

The isolated browser harness lives in `tests/visual-engine-browser/` and runs against Vite without mounting the workbench into the production application. GitHub Actions installs Playwright browsers at job time without adding runtime dependencies or changing the application lockfile. Current automated coverage includes:

- WebGL2 Ambient Flow and Particle Field plus Canvas 2D Aurora rendering.
- Search and category filtering.
- Preset selection, range controls, reset, and JSON import/export, including oversized import rejection.
- Responsive layout at desktop and mobile emulated viewports.
- Canvas resize behavior.
- Hidden-tab pause/resume and reduced-motion pause/resume.
- WebGL context-loss recovery.
- Renderer switching and disposal of the previous animation loop.

The latest PR #2 CI run completed successfully: build, ESLint, Chromium desktop/mobile, Firefox Canvas 2D, and WebKit Canvas 2D. The CI browser runtime uses Chromium's software WebGL implementation. It provides repeatable API/browser coverage but is not a substitute for real-device GPU, browser-vendor, thermal, or long-duration performance testing.

## Required manual release verification

Complete this checklist on a non-production preview build before considering production integration:

- [ ] Test WebGL2 on at least one physical desktop/laptop GPU in current Chrome or Edge.
- [ ] Test WebGL2 on at least one physical mobile device with a supported browser.
- [ ] Test Canvas 2D fallback on a browser/device where WebGL2 is unavailable or disabled.
- [ ] Switch repeatedly between all effects; confirm no frozen canvas, stale animation, or steadily increasing resource use.
- [ ] Resize, rotate, background/foreground the tab, and exercise reduced-motion settings.
- [ ] Trigger context loss/recovery where the browser exposes the test extension; confirm graceful fallback if recovery fails.
- [ ] Inspect console errors and GPU/process memory during a sustained preview session.
- [ ] Confirm the preview remains isolated and does not change clip analysis, render, upload, or export workflows.

Record browser/version, device/GPU, operating system, renderer used, and any observed errors with the verification result. Do not mark physical GPU validation complete based only on software WebGL CI.
