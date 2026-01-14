"use client";

/**
 * Post-processing effects rig for cinematic dashboard
 * Uses @react-three/postprocessing for GPU-efficient effects
 */

import { useThree } from "@react-three/fiber";
import {
  EffectComposer,
  Bloom,
  Noise,
  Vignette,
} from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import * as THREE from "three";
import { useEffect } from "react";

export function EffectsRig() {
  const { gl } = useThree();

  useEffect(() => {
    // Configure renderer for cinematic output
    gl.outputColorSpace = THREE.SRGBColorSpace;
    gl.toneMapping = THREE.ACESFilmicToneMapping;
    gl.toneMappingExposure = 1.0;
  }, [gl]);

  return (
    <EffectComposer multisampling={0}>
      <Bloom
        intensity={0.4}
        luminanceThreshold={0.2}
        luminanceSmoothing={0.9}
        mipmapBlur
      />
      <Noise
        premultiply
        blendFunction={BlendFunction.SCREEN}
        opacity={0.06}
      />
      <Vignette
        eskil={false}
        offset={0.3}
        darkness={0.8}
      />
    </EffectComposer>
  );
}
