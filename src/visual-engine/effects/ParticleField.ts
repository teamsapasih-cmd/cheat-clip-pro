import { createProgram } from "../shaders";
import type { VisualEffectFactory } from "../types";

const vertexShader = `#version 300 es
precision highp float;
const vec2 POSITIONS[3] = vec2[3](vec2(-1.0,-1.0), vec2(3.0,-1.0), vec2(-1.0,3.0));
out vec2 vUv;
void main() { vec2 p = POSITIONS[gl_VertexID]; vUv = p * 0.5 + 0.5; gl_Position = vec4(p,0.0,1.0); }
`;
const fragmentShader = `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 outColor;
uniform vec2 uResolution;
uniform float uTime;
uniform float uMotion;
uniform float uIntensity;
uniform float uSize;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
void main() {
  vec2 aspect = vec2(uResolution.x / max(uResolution.y,1.0), 1.0);
  vec2 p = (vUv - 0.5) * aspect;
  vec2 grid = vec2(54.0, 34.0);
  vec2 cell = floor((vUv - 0.5) * grid + grid * 0.5);
  vec2 local = fract((vUv - 0.5) * grid + grid * 0.5) - 0.5;
  float seed = hash(cell);
  float phase = uTime * uMotion * (0.35 + seed * 0.8);
  vec2 drift = vec2(sin(phase + seed * 6.28), cos(phase * 0.8 + seed * 9.0)) * 0.12;
  float radius = 0.055 * uSize * (0.55 + 0.45 * sin(phase + seed * 8.0));
  float distanceToPoint = length(local - drift);
  float dotShape = 1.0 - smoothstep(radius * 0.35, radius, distanceToPoint);
  float wave = 0.5 + 0.5 * sin(length(p) * 9.0 - uTime * uMotion * 1.4);
  float alpha = dotShape * (0.25 + wave * 0.75) * uIntensity;
  vec3 color = mix(vec3(0.22,0.62,0.82), vec3(0.66,0.48,0.96), seed);
  vec3 background = vec3(0.055,0.075,0.15);
  outColor = vec4(mix(background, color, alpha), 1.0);
}
`;

export interface ParticleFieldOptions { motion?: number; intensity?: number; size?: number; }
export const createParticleFieldEffect = (options: ParticleFieldOptions = {}): VisualEffectFactory => (gl) => {
  const program = createProgram(gl, vertexShader, fragmentShader);
  const vao = gl.createVertexArray();
  if (!vao) { gl.deleteProgram(program); throw new Error("Unable to allocate the particle vertex array."); }
  const resolution = gl.getUniformLocation(program, "uResolution");
  const time = gl.getUniformLocation(program, "uTime");
  const motionLocation = gl.getUniformLocation(program, "uMotion");
  const intensityLocation = gl.getUniformLocation(program, "uIntensity");
  const sizeLocation = gl.getUniformLocation(program, "uSize");
  const motion = Math.min(1, Math.max(0, options.motion ?? 0.5));
  const intensity = Math.min(1, Math.max(0.1, options.intensity ?? 0.8));
  const size = Math.min(2, Math.max(0.5, options.size ?? 1));
  let width = 1; let height = 1;
  return {
    resize(nextWidth, nextHeight) { width = nextWidth; height = nextHeight; },
    render(frame) {
      gl.useProgram(program); gl.bindVertexArray(vao);
      gl.uniform2f(resolution, width * frame.pixelRatio, height * frame.pixelRatio);
      gl.uniform1f(time, frame.time); gl.uniform1f(motionLocation, motion);
      gl.uniform1f(intensityLocation, intensity); gl.uniform1f(sizeLocation, size);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
    dispose() { gl.bindVertexArray(null); gl.deleteVertexArray(vao); gl.deleteProgram(program); },
  };
};
