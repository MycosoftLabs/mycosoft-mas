"use client";

import * as THREE from "three";
import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";

type GlobeArc = {
  from: [number, number]; // [lat, lon] degrees
  to: [number, number];   // [lat, lon] degrees
  strength?: number;      // visual weight
};

type Props = {
  radius?: number;
  pointCount?: number;
  color?: string;
  opacity?: number;
  rotationSpeed?: number;
  orbitBands?: number;     // how many orbital rings
  arcs?: GlobeArc[];       // optional network arcs
  arcCountCap?: number;    // safety cap for total arc segments
};

const globeVert = /* glsl */ `
precision highp float;

attribute float aSeed;

uniform float uTime;
uniform float uRadius;

varying float vTwinkle;

float hash11(float p) {
  p = fract(p * 0.1031);
  p *= p + 33.33;
  p *= p + p;
  return fract(p);
}

void main() {
  vec3 p = position;

  // subtle breathing + twinkle
  float tw = 0.55 + 0.45 * sin(uTime * (0.8 + hash11(aSeed) * 1.4) + aSeed * 6.2831);
  vTwinkle = tw;

  // gentle radial noise to keep it organic
  p = normalize(p) * (uRadius + (tw - 0.5) * 0.12);

  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;

  // size in screen space (clamped)
  float size = 2.2 + 2.6 * tw;
  gl_PointSize = size * (300.0 / max(120.0, -mv.z));
}
`;

const globeFrag = /* glsl */ `
precision highp float;

uniform vec3 uColor;
uniform float uOpacity;

varying float vTwinkle;

void main() {
  // circular point sprite with soft edge
  vec2 uv = gl_PointCoord.xy - 0.5;
  float d = length(uv);
  float core = smoothstep(0.5, 0.0, d);

  float a = uOpacity * core * (0.35 + 0.65 * vTwinkle);
  gl_FragColor = vec4(uColor, a);
}
`;

// Orbit bands: cheap "particle ring" with shader twinkle
const ringVert = /* glsl */ `
precision highp float;

attribute float aSeed;

uniform float uTime;
uniform float uRadius;

varying float vA;

float hash11(float p) {
  p = fract(p * 0.1031);
  p *= p + 33.33;
  p *= p + p;
  return fract(p);
}

void main() {
  vec3 p = position;
  float tw = 0.6 + 0.4 * sin(uTime * (0.9 + 1.2 * hash11(aSeed)) + aSeed * 10.0);
  vA = tw;

  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;

  gl_PointSize = (1.8 + 2.2 * tw) * (280.0 / max(120.0, -mv.z));
}
`;

const ringFrag = /* glsl */ `
precision highp float;

uniform vec3 uColor;
uniform float uOpacity;

varying float vA;

void main() {
  vec2 uv = gl_PointCoord.xy - 0.5;
  float d = length(uv);
  float core = smoothstep(0.5, 0.0, d);
  float a = uOpacity * core * (0.25 + 0.75 * vA);
  gl_FragColor = vec4(uColor, a);
}
`;

function latLonToVec3(lat: number, lon: number, r: number) {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);
  const x = -r * Math.sin(phi) * Math.cos(theta);
  const z = r * Math.sin(phi) * Math.sin(theta);
  const y = r * Math.cos(phi);
  return new THREE.Vector3(x, y, z);
}

function makeFibonacciSpherePoints(count: number, r: number) {
  const pts = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = golden * i;
    const x = Math.cos(theta) * radius;
    const z = Math.sin(theta) * radius;
    pts[i * 3 + 0] = x * r;
    pts[i * 3 + 1] = y * r;
    pts[i * 3 + 2] = z * r;
    seeds[i] = i / count;
  }
  return { pts, seeds };
}

function makeOrbitRingPoints(r: number, count: number, tilt: THREE.Euler, yOffset = 0) {
  const pts = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  const q = new THREE.Quaternion().setFromEuler(tilt);
  const v = new THREE.Vector3();
  for (let i = 0; i < count; i++) {
    const t = (i / count) * Math.PI * 2;
    v.set(Math.cos(t) * r, yOffset, Math.sin(t) * r).applyQuaternion(q);
    pts[i * 3 + 0] = v.x;
    pts[i * 3 + 1] = v.y;
    pts[i * 3 + 2] = v.z;
    seeds[i] = i / count;
  }
  return { pts, seeds };
}

function makeArcLine(fromLL: [number, number], toLL: [number, number], r: number, segments: number) {
  const a = latLonToVec3(fromLL[0], fromLL[1], r);
  const b = latLonToVec3(toLL[0], toLL[1], r);

  // arc control point pushes outward to feel "orbital"
  const mid = a.clone().add(b).multiplyScalar(0.5);
  const lift = mid.clone().normalize().multiplyScalar(r * 0.35);
  const c = mid.add(lift);

  const curve = new THREE.QuadraticBezierCurve3(a, c, b);
  const pts = curve.getPoints(segments);
  const arr = new Float32Array(pts.length * 3);
  for (let i = 0; i < pts.length; i++) {
    arr[i * 3 + 0] = pts[i].x;
    arr[i * 3 + 1] = pts[i].y;
    arr[i * 3 + 2] = pts[i].z;
  }
  return arr;
}

export function ParticleGlobe({
  radius = 2.25,
  pointCount = 16000,
  color = "#d7dcff",
  opacity = 0.55,
  rotationSpeed = 0.12,
  orbitBands = 3,
  arcs = [],
  arcCountCap = 400,
}: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const matRef = useRef<THREE.ShaderMaterial>(null);
  const ringMats = useRef<THREE.ShaderMaterial[]>([]);
  const arcMatRef = useRef<THREE.LineBasicMaterial>(null);

  const uColor = useMemo(() => new THREE.Color(color), [color]);

  const globeGeom = useMemo(() => {
    const { pts, seeds } = makeFibonacciSpherePoints(pointCount, radius);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    return g;
  }, [pointCount, radius]);

  const rings = useMemo(() => {
    const items: { geom: THREE.BufferGeometry; speed: number }[] = [];
    const ringPoints = Math.min(9000, Math.max(2500, Math.floor(pointCount * 0.35)));

    for (let i = 0; i < orbitBands; i++) {
      const tilt = new THREE.Euler(
        (i * 0.35 + 0.25) * Math.PI * 0.35,
        (i * 0.22) * Math.PI * 0.35,
        0
      );
      const yOffset = (i - (orbitBands - 1) / 2) * (radius * 0.18);
      const { pts, seeds } = makeOrbitRingPoints(radius * (1.05 + i * 0.06), ringPoints, tilt, yOffset);
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pts, 3));
      g.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
      items.push({ geom: g, speed: 0.06 + 0.04 * i });
    }
    return items;
  }, [orbitBands, pointCount, radius]);

  const arcGeometry = useMemo(() => {
    if (!arcs.length) return null;

    // Merge arcs into one line segments buffer for performance
    const safe = arcs.slice(0, arcCountCap);
    const segsPerArc = 48;

    const all: number[] = [];
    for (const a of safe) {
      const arr = makeArcLine(a.from, a.to, radius * 1.02, segsPerArc);
      // as a continuous line strip, push points
      for (let i = 0; i < arr.length; i++) all.push(arr[i]);
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(all, 3));
    return g;
  }, [arcs, arcCountCap, radius]);

  useFrame((_, dt) => {
    if (matRef.current) matRef.current.uniforms.uTime.value += dt;
    for (const m of ringMats.current) if (m) m.uniforms.uTime.value += dt;

    if (groupRef.current) {
      groupRef.current.rotation.y += dt * rotationSpeed;
      groupRef.current.rotation.x += dt * rotationSpeed * 0.12;
    }
  });

  return (
    <group ref={groupRef}>
      <points geometry={globeGeom}>
        <shaderMaterial
          ref={matRef}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          vertexShader={globeVert}
          fragmentShader={globeFrag}
          uniforms={{
            uTime: { value: 0 },
            uRadius: { value: radius },
            uColor: { value: uColor },
            uOpacity: { value: opacity },
          }}
        />
      </points>

      {rings.map((r, i) => (
        <points key={i} geometry={r.geom}>
          <shaderMaterial
            ref={(m: any) => {
              if (m) ringMats.current[i] = m;
            }}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            vertexShader={ringVert}
            fragmentShader={ringFrag}
            uniforms={{
              uTime: { value: 0 },
              uRadius: { value: radius },
              uColor: { value: uColor },
              uOpacity: { value: opacity * 0.7 },
            }}
          />
        </points>
      ))}

      {arcGeometry ? (
        <line>
          <bufferGeometry attach="geometry" {...arcGeometry} />
          <lineBasicMaterial
            ref={arcMatRef}
            transparent
            opacity={0.18}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            color={uColor}
          />
        </line>
      ) : null}
    </group>
  );
}
