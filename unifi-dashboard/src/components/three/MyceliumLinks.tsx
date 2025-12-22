"use client";

import * as THREE from "three";
import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";

type Node = { id: string; position: [number, number, number] };
type Link = { source: string; target: string; weight?: number; type?: string };

type Props = {
  nodes: Node[];
  links: Link[];
  /** Visual scale for your scene */
  scale?: number;
  /** How "organic" paths are */
  curl?: number;
  /** How many curve subdivisions per link */
  segmentsPerLink?: number;
  /** How many micro-branches to sprinkle */
  fuzz?: number;
  /** Base color (will be modulated in shader) */
  color?: string;
};

function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashStringToSeed(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

const vert = /* glsl */ `
precision highp float;

attribute vec3 instanceStart;
attribute vec3 instanceEnd;
attribute float instancePhase;
attribute float instanceWidth;
attribute float instanceJitter;

uniform mat4 modelViewMatrix;
uniform mat4 projectionMatrix;
uniform float uTime;
uniform float uScale;

varying float vAlong;
varying float vPhase;
varying float vWidth;
varying float vFlicker;

float hash11(float p) {
  p = fract(p * 0.1031);
  p *= p + 33.33;
  p *= p + p;
  return fract(p);
}

vec3 noiseVec3(float x) {
  return vec3(hash11(x), hash11(x + 17.0), hash11(x + 37.0)) * 2.0 - 1.0;
}

void main() {
  // position in [0..1] along a segment
  float t = position.x; // we encode a 1D line segment into position.x
  vec3 p = mix(instanceStart, instanceEnd, t);

  // organic wobble: bend the strand slightly in 3D
  float tt = (t + instancePhase * 0.13);
  vec3 n = noiseVec3(tt * 10.0 + instanceJitter * 100.0);
  float wob = 0.07 * uScale;
  p += n * wob * (sin((uTime * 0.9) + tt * 6.2831) * 0.5 + 0.5);

  // subtle thickness illusion: push a tiny bit in view-space normal direction
  // (cheap "tube-ish" feel without actual tubes)
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  vec3 viewDir = normalize(-mv.xyz);
  vec3 side = normalize(cross(viewDir, vec3(0.0, 1.0, 0.0)));
  float w = instanceWidth * (0.6 + 0.4 * sin(uTime * 1.7 + instancePhase));
  mv.xyz += side * (w * 0.0025);

  vAlong = t;
  vPhase = instancePhase;
  vWidth = instanceWidth;

  // random-ish flicker per segment
  vFlicker = 0.7 + 0.3 * sin(uTime * 2.0 + instancePhase * 12.0);

  gl_Position = projectionMatrix * mv;
}
`;

const frag = /* glsl */ `
precision highp float;

uniform vec3 uColor;
uniform float uTime;
uniform float uGlow;
uniform float uOpacity;

varying float vAlong;
varying float vPhase;
varying float vWidth;
varying float vFlicker;

float smoothPulse(float x, float w) {
  // smooth moving highlight along the strand
  float d = abs(fract(x) - 0.5);
  return smoothstep(w, 0.0, d);
}

void main() {
  // base fade at strand ends (more biological / less "cable")
  float endFade = smoothstep(0.0, 0.08, vAlong) * (1.0 - smoothstep(0.92, 1.0, vAlong));

  // traveling "nutrient" pulse
  float travel = fract(vAlong * 1.7 - uTime * (0.25 + 0.15 * sin(vPhase)));
  float pulse = smoothPulse(travel, 0.18);

  // gentle breathing
  float breathe = 0.65 + 0.35 * sin(uTime * 1.1 + vPhase * 3.0);

  // glow-ish intensity (no postprocessing needed)
  float intensity = (0.35 + 0.9 * pulse) * breathe * vFlicker * endFade;

  // slight color shift toward cooler highlights
  vec3 col = uColor;
  col += vec3(0.15, 0.2, 0.35) * pulse;

  float alpha = uOpacity * (0.12 + 0.88 * intensity);

  // Fake "softness" by modulating alpha with glow factor
  alpha *= mix(0.6, 1.0, uGlow);

  gl_FragColor = vec4(col, alpha);
}
`;

export function MyceliumLinks({
  nodes,
  links,
  scale = 1,
  curl = 1.0,
  segmentsPerLink = 22,
  fuzz = 0.35,
  color = "#cfd6ff",
}: Props) {
  const matRef = useRef<THREE.ShaderMaterial>(null);

  const { geom, count } = useMemo(() => {
    const nodeMap = new Map(nodes.map((n) => [n.id, new THREE.Vector3(...n.position)]));

    // We'll generate MANY short segments (line segments) from each curved link
    const starts: number[] = [];
    const ends: number[] = [];
    const phase: number[] = [];
    const width: number[] = [];
    const jitter: number[] = [];

    const addSegment = (a: THREE.Vector3, b: THREE.Vector3, ph: number, w: number, j: number) => {
      starts.push(a.x, a.y, a.z);
      ends.push(b.x, b.y, b.z);
      phase.push(ph);
      width.push(w);
      jitter.push(j);
    };

    for (const L of links) {
      const A = nodeMap.get(L.source);
      const B = nodeMap.get(L.target);
      if (!A || !B) continue;

      const seed = hashStringToSeed(`${L.source}->${L.target}`);
      const rnd = mulberry32(seed);

      // Build an organic spline between A and B
      const dir = new THREE.Vector3().subVectors(B, A);
      const dist = dir.length();
      const mid = new THREE.Vector3().addVectors(A, B).multiplyScalar(0.5);

      // Two control points offset perpendicular-ish to direction
      const up = new THREE.Vector3(0, 1, 0);
      const side = new THREE.Vector3().crossVectors(dir.clone().normalize(), up).normalize();
      if (side.lengthSq() < 1e-6) side.set(1, 0, 0);

      const bend = (0.08 + 0.18 * rnd()) * dist * curl;
      const c1 = mid.clone()
        .add(side.clone().multiplyScalar((rnd() - 0.5) * bend))
        .add(up.clone().multiplyScalar((rnd() - 0.5) * bend * 0.6));
      const c2 = mid.clone()
        .add(side.clone().multiplyScalar((rnd() - 0.5) * bend))
        .add(up.clone().multiplyScalar((rnd() - 0.5) * bend * 0.6));

      const curve = new THREE.CatmullRomCurve3([A, c1, c2, B], false, "catmullrom", 0.65);

      const pts = curve.getPoints(segmentsPerLink);
      const ph = rnd() * 10.0;
      const baseW = (L.weight ?? 1) * (0.7 + 0.9 * rnd());
      const j = rnd();

      for (let i = 0; i < pts.length - 1; i++) {
        addSegment(pts[i], pts[i + 1], ph + i * 0.02, baseW, j);
      }

      // Fuzz: micro-branches that shoot off the main strand
      // Keep it sparse so it reads as mycelium, not spaghetti.
      const fuzzCount = Math.floor((pts.length - 1) * fuzz * (0.15 + 0.85 * rnd()));
      for (let k = 0; k < fuzzCount; k++) {
        const idx = 1 + Math.floor(rnd() * (pts.length - 2));
        const p = pts[idx];
        const q = pts[idx + 1];
        const tangent = q.clone().sub(p).normalize();

        const n1 = new THREE.Vector3().crossVectors(tangent, up).normalize();
        if (n1.lengthSq() < 1e-6) n1.set(1, 0, 0);
        const n2 = new THREE.Vector3().crossVectors(tangent, n1).normalize();

        const branchLen = (0.03 + 0.12 * rnd()) * dist;
        const branchDir = n1.multiplyScalar((rnd() - 0.5)).add(n2.multiplyScalar((rnd() - 0.5))).normalize();

        const bEnd = p.clone().add(branchDir.multiplyScalar(branchLen));
        // slightly thinner branches
        addSegment(p, bEnd, ph + 5.0 + k * 0.11, baseW * 0.45, j + k * 0.01);
      }
    }

    // Base geometry is a 1D segment: position.x is [0..1], used in the shader
    const base = new THREE.BufferGeometry();
    const basePos = new Float32Array([0, 0, 0, 1, 0, 0]);
    base.setAttribute("position", new THREE.BufferAttribute(basePos, 3));

    const g = new THREE.InstancedBufferGeometry();
    g.index = base.index;
    g.setAttribute("position", base.getAttribute("position"));

    g.setAttribute("instanceStart", new THREE.InstancedBufferAttribute(new Float32Array(starts), 3));
    g.setAttribute("instanceEnd", new THREE.InstancedBufferAttribute(new Float32Array(ends), 3));
    g.setAttribute("instancePhase", new THREE.InstancedBufferAttribute(new Float32Array(phase), 1));
    g.setAttribute("instanceWidth", new THREE.InstancedBufferAttribute(new Float32Array(width), 1));
    g.setAttribute("instanceJitter", new THREE.InstancedBufferAttribute(new Float32Array(jitter), 1));

    return { geom: g, count: phase.length };
  }, [nodes, links, curl, segmentsPerLink, fuzz]);

  const uColor = useMemo(() => new THREE.Color(color), [color]);

  useFrame((_, dt) => {
    const m = matRef.current;
    if (!m) return;
    m.uniforms.uTime.value += dt;
  });

  return (
    <lineSegments args={[geom]}>
      <shaderMaterial
        ref={matRef}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        vertexShader={vert}
        fragmentShader={frag}
        uniforms={{
          uTime: { value: 0 },
          uScale: { value: scale },
          uColor: { value: uColor },
          uGlow: { value: 0.9 },
          uOpacity: { value: 0.65 },
        }}
      />
    </lineSegments>
  );
}
