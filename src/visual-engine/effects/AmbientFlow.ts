import { createProgram } from "../shaders";
import type { VisualEffectFactory } from "../types";

const vertexShader = \`#version 300 es
precision highp float;
const vec2 POSITIONS[3] = vec2[3](
  vec2(-1.0, -1.0),
  vec2(3.0, -1.0),
  vec2(-1.0, 3.0)
);
out vec2 vUv;
void main() {
  vec2 position = POSITIONS[gl_VertexID];
  vUv = position * 0.5 + 0.5;
  gl_Position = vec4(position, 0.0, 1.0);
}\`;

const fragmentShader = \`#version 300 es
precision highp float;
in vec2 vUv;
out vec4 outColor;
uniform vec2 uResolution;
uniform vec2 uPointer;
uniform float uTime;
uniform float uMotion;
uniform float uIntensity;
uniform float uPointerResponse;

float field(vec2 p, float t) {
  float a = sin(p.x * 2.4 + t * 0.38);
  float b = cos(p.y * 2.0 - t * 0.31);
  float c = sin((p.x + p.y) * 1.6 + t * 0.22);
  return (a + b + c) / 3.0;
}

void main() {
  vec2 uv = vUv;
  vec2 aspect = vec2(uResolution.x / max(uResolution.y, 1.0), 1.0);
  vec2 p = (uv - 0.5) * aspect;
  float wave = field(p * 2.0, uTime * uMotion);
  float pointerGlow = (1.0 - smoothstep(0.0, 0.8, distance(p, (uPointer - 0.5) * aspect))) * uPointerResponse;
  float blend = clamp(0.5 + wave * 0.34 * uIntensity + pointerGlow * 0.12, 0.0, 1.0);

  vec3 deep = vec3(0.12, 0.18, 0.42);
  vec3 violet = vec3(0.43, 0.29, 0.78);
  vec3 cyan = vec3(0.20, 0.68, 0.78);
  vec3 color = mix(deep, violet, smoothstep(0.08, 0.72, blend));
  color = mix(color, cyan, smoothstep(0.62, 0.98, blend) * 0.48);
  float vignette = 1.0 - smoothstep(0.25, 0.95, length((uv - 0.5) * aspect));
  color *= 0.72 + vignette * 0.28;
  outColor = vec4(color, 1.0);
}\`;

export interface AmbientFlowOptions {
  motion?: number;
  intensity?: number;
  pointerResponse?: boolean;
}

export const createAmbientFlowEffect = (options: AmbientFlowOptions = {}): VisualEffectFactory => (gl) => {
  const program = createProgram(gl, vertexShader, fragmentShader);
  const vertexArray = gl.createVertexArray();
  if (!vertexArray) {
    gl.deleteProgram(program);
    throw new Error("Unable to allocate the visual vertex array.");
  }

  const resolutionLocation = gl.getUniformLocation(program, "uResolution");
  const pointerLocation = gl.getUniformLocation(program, "uPointer");
  const timeLocation = gl.getUniformLocation(program, "uTime");
  const motionLocation = gl.getUniformLocation(program, "uMotion");
  const intensityLocation = gl.getUniformLocation(program, "uIntensity");
  const pointerResponseLocation = gl.getUniformLocation(program, "uPointerResponse");
  const motion = Math.min(1, Math.max(0, options.motion ?? 0.55));
  const intensity = Math.min(1, Math.max(0.2, options.intensity ?? 0.8));
  const pointerResponse = options.pointerResponse === false ? 0 : 1;
  let width = 1;
  let height = 1;

  return {
    resize(nextWidth, nextHeight) {
      width = nextWidth;
      height = nextHeight;
    },
    render(frame) {
      gl.useProgram(program);
      gl.bindVertexArray(vertexArray);
      gl.uniform2f(resolutionLocation, width * frame.pixelRatio, height * frame.pixelRatio);
      gl.uniform2f(pointerLocation, frame.pointer.x, frame.pointer.y);
      gl.uniform1f(timeLocation, frame.time);
      gl.uniform1f(motionLocation, motion);
      gl.uniform1f(intensityLocation, intensity);
      gl.uniform1f(pointerResponseLocation, pointerResponse);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    },
    dispose() {
      gl.bindVertexArray(null);
      gl.deleteVertexArray(vertexArray);
      gl.deleteProgram(program);
    },
  };
};
