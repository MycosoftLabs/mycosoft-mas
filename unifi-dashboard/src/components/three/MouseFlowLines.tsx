"use client";

import * as THREE from "three";
import React, { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";

type Props = {
  /** Bounds of the field in world units */
  width?: number;
  height?: number;
  /** Number of strands */
  strandCount?: number;
  /** Strand length range */
  strandLength?: [number, number];
  /** Visual tuning */
  color?: string;
  opacity?: number;
  /** How strongly mouse affects nearby strands */
  influenceRadius?: number;
  /** Where the interaction plane should sit */
  planeZ?: number;
};

const vert = /* glsl */ `
precision highp float;

attribute vec3 instanceStart;
attribute vec3 instanceEnd;
attribute float instanceSeed;

uniform float uTime;
uniform vec3 uMouse;
uniform float uInfluence;
uniform float uRadius;

varying float vNear;
varying float vAlong;

float hash11(float p) {
  p = fract(p * 0.1031);
  p *= p + 33.33;
  p *= p + p;
  return fract(p);
}

void main() {
  // t along the segment encoded in position.x: 0..1
  float t = position.x;
  vec3 p = mix(instanceStart, instanceEnd, t);

  // Distance to mouse attractor
  float d = length(p - uMouse);
  float near = 1.0 - smoothstep(0.0, uRadius, d);
  vNear = near;
  vAlong = t;

  // Flow: push along strand direction + small swirl near mouse
  vec3 dir = normalize(instanceEnd - instanceStart);
  float speed = 0.35 + 0.9 * hash11(instanceSeed);
  float phase = instanceSeed * 12.0;

  float flow = sin(uTime * speed + phase + t * 6.2831);
  p += dir * flow * 0.05;

  // Swirl near mouse
  vec3 toM = normalize(p - uMouse);
  vec3 swirlAxis = vec3(0.0, 0.0, 1.0);
  vec3 swirl = normalize(cross(swirlAxis, toM));
  p += swirl * near * uInfluence * 0.12;

  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
}
`;

const frag = /* glsl */ `
precision highp float;

uniform vec3 uColor;
uniform float uOpacity;
uniform float uTime;

varying float vNear;
varying float vAlong;

float smoothPulse(float x, float w) {
  float d = abs(fract(x) - 0.5);
  return smoothstep(w, 0.0, d);
}

void main() {
  // traveling pulse along strand
  float travel = fract(vAlong * 1.6 - uTime * 0.35);
  float pulse = smoothPulse(travel, 0.18);

  // Fade ends
  float endFade = smoothstep(0.0, 0.12, vAlong) * (1.0 - smoothstep(0.88, 1.0, vAlong));

  float intensity = (0.18 + 0.82 * pulse) * endFade;

  // Mouse proximity boosts brightness
  intensity *= (1.0 + 2.2 * vNear);

  float a = uOpacity * intensity;
  gl_FragColor = vec4(uColor, a);
}
`;

export function MouseFlowLines({
  width = 12,
  height = 7,
  strandCount = 2400,
  strandLength = [0.25, 1.2],
  color = "#d7dcff",
  opacity = 0.35,
  influenceRadius = 2.0,
  planeZ = 0,
}: Props) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const matRef = useRef<THREE.ShaderMaterial>(null);
  const { camera, pointer, raycaster } = useThree();

  const mouseWorld = useRef(new THREE.Vector3(0, 0, planeZ));
  const hitPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 0, 1), -planeZ), [planeZ]);
  const tmpVec = useMemo(() => new THREE.Vector3(), []);
  const uColor = useMemo(() => new THREE.Color(color), [color]);

  const { geom, count } = useMemo(() => {
    // Base 1D segment; shader uses position.x as t in [0..1]
    const base = new THREE.BufferGeometry();
    base.setAttribute(
      "position",
      new THREE.BufferAttribute(new Float32Array([0, 0, 0, 1, 0, 0]), 3)
    );

    const starts: number[] = [];
    const ends: number[] = [];
    const seeds: number[] = [];

    const rnd = (i: number) => {
      // stable pseudo-random
      const x = Math.sin(i * 999.123) * 43758.5453;
      return x - Math.floor(x);
    };

    for (let i = 0; i < strandCount; i++) {
      const rx = (rnd(i + 1) - 0.5) * width;
      const ry = (rnd(i + 2) - 0.5) * height;

      const len = THREE.MathUtils.lerp(strandLength[0], strandLength[1], rnd(i + 3));
      const ang = rnd(i + 4) * Math.PI * 2;

      const sx = rx;
      const sy = ry;
      const ex = rx + Math.cos(ang) * len;
      const ey = ry + Math.sin(ang) * len;

      starts.push(sx, sy, planeZ);
      ends.push(ex, ey, planeZ);

      seeds.push(i / strandCount);
    }

    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute("position", base.getAttribute("position"));
    g.setAttribute("instanceStart", new THREE.InstancedBufferAttribute(new Float32Array(starts), 3));
    g.setAttribute("instanceEnd", new THREE.InstancedBufferAttribute(new Float32Array(ends), 3));
    g.setAttribute("instanceSeed", new THREE.InstancedBufferAttribute(new Float32Array(seeds), 1));

    return { geom: g, count: strandCount };
  }, [strandCount, width, height, strandLength, planeZ]);

  useFrame((_, dt) => {
    // raycast pointer to plane in world space
    raycaster.setFromCamera(pointer, camera);
    raycaster.ray.intersectPlane(hitPlane, tmpVec);
    mouseWorld.current.copy(tmpVec);

    if (matRef.current) {
      matRef.current.uniforms.uTime.value += dt;
      matRef.current.uniforms.uMouse.value.copy(mouseWorld.current);
    }
  });

  return (
    <instancedMesh ref={meshRef} args={[geom, undefined as unknown as THREE.Material, count]}>
      <shaderMaterial
        ref={matRef}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        vertexShader={vert}
        fragmentShader={frag}
        uniforms={{
          uTime: { value: 0 },
          uMouse: { value: new THREE.Vector3(0, 0, planeZ) },
          uInfluence: { value: 1.0 },
          uRadius: { value: influenceRadius },
          uColor: { value: uColor },
          uOpacity: { value: opacity },
        }}
      />
    </instancedMesh>
  );
}
