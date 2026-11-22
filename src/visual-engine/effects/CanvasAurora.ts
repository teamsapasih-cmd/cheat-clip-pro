import type { Canvas2DEffectFactory } from "../types";
export const createCanvasAuroraEffect = (): Canvas2DEffectFactory => () => ({
  render({ ctx, time, width, height, pointer }) {
    const t = time * 0.16; const sx = pointer.active ? (pointer.x - 0.5) * 34 : 0; const sy = pointer.active ? (pointer.y - 0.5) * 22 : 0;
    ctx.fillStyle = "#101326"; ctx.fillRect(0, 0, width, height);
    const glow = (x: number, y: number, radius: number, inner: string) => { const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius); gradient.addColorStop(0, inner); gradient.addColorStop(1, "rgba(0,0,0,0)"); ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height); };
    glow(width * (0.28 + Math.sin(t) * 0.08) + sx, height * (0.36 + Math.cos(t * 0.8) * 0.08) + sy, Math.max(width, height) * 0.78, "rgba(105,86,220,0.58)");
    glow(width * (0.72 + Math.cos(t * 0.7) * 0.07) - sx, height * (0.68 + Math.sin(t * 0.9) * 0.08) - sy, Math.max(width, height) * 0.72, "rgba(37,190,190,0.42)");
    glow(width * 0.5, height * (0.45 + Math.sin(t * 0.5) * 0.05), Math.max(width, height) * 0.52, "rgba(180,105,205,0.24)");
  },
});
