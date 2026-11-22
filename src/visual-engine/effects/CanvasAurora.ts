import type { Canvas2DEffectFactory } from "../types";

export interface CanvasAuroraOptions {
  motion?: number;
  intensity?: number;
  pointerResponse?: boolean;
}

export const createCanvasAuroraEffect = (options: CanvasAuroraOptions = {}): Canvas2DEffectFactory => {
  const motion = Math.min(1, Math.max(0, options.motion ?? 0.55));
  const intensity = Math.min(1, Math.max(0.2, options.intensity ?? 0.8));
  const pointerResponse = options.pointerResponse !== false;

  return () => ({
    render({ ctx, time, width, height, pointer }) {
      const t = time * motion;
      const sx = pointerResponse && pointer.active ? (pointer.x - 0.5) * 34 : 0;
      const sy = pointerResponse && pointer.active ? (pointer.y - 0.5) * 22 : 0;
      ctx.fillStyle = "#101326";
      ctx.fillRect(0, 0, width, height);

      const glow = (x: number, y: number, radius: number, inner: string) => {
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
        gradient.addColorStop(0, inner);
        gradient.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
      };

      glow(width * (0.28 + Math.sin(t * 0.65) * 0.08) + sx, height * (0.36 + Math.cos(t * 0.52) * 0.08) + sy, Math.max(width, height) * 0.78, `rgba(105,86,220,${0.58 * intensity})`);
      glow(width * (0.72 + Math.cos(t * 0.48) * 0.07) - sx, height * (0.68 + Math.sin(t * 0.58) * 0.08) - sy, Math.max(width, height) * 0.72, `rgba(37,190,190,${0.42 * intensity})`);
      glow(width * 0.5, height * (0.45 + Math.sin(t * 0.32) * 0.05), Math.max(width, height) * 0.52, `rgba(180,105,205,${0.24 * intensity})`);
    },
  });
};
