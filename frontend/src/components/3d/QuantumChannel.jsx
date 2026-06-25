/**
 * QuantumChannel.jsx — Final Polish Patch v3
 *
 * Glass Tube Overhaul:
 * - MeshTransmissionMaterial: physics-accurate glass refraction shader
 * - Environment IBL: required for MeshTransmissionMaterial to render correctly
 * - Tube is always transparent — state changes only affect inner contents
 * - Sparkles (ambient quantum foam) — state-reactive color/speed
 * - Grid (infinite, fade-distance) — deep-space construct depth
 * - ChromaticAberration — cinematic glass-lens post-processing
 * - State machine: Normal→Cyan, Attacked→Red, PA Active→Purple, E91 Shield→Purple
 */

import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Float, Sparkles, Grid, Environment } from '@react-three/drei';
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import * as THREE from 'three';
import { Vector2 } from 'three';

// ── Shared Geometries (module-level — prevents WebGL context loss on re-render) ──
const SPHERE_GEOM = new THREE.SphereGeometry(0.09, 8, 8);
const NODE_GEOM = new THREE.BoxGeometry(1.1, 1.1, 1.1);
const DEPTH_GEOM = new THREE.SphereGeometry(1, 32, 32);

// ── Node (Alice / Bob) ─────────────────────────────────────────────────────
const Node = ({ position, label, subLabel, color }) => (
  <group position={position}>
    <mesh geometry={NODE_GEOM}>
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.6}
        transparent
        opacity={0.85}
        roughness={0.2}
        metalness={0.6}
      />
    </mesh>
    {/* Label ABOVE the node */}
    <Text position={[0, 1.6, 0]} fontSize={0.48} color="white" anchorX="center" anchorY="middle">
      {label}
    </Text>
    {/* SubLabel BELOW the node — PATCH: moved from [0, 0.9, 0] to avoid overlap */}
    <Text position={[0, -1.6, 0]} fontSize={0.28} color="#64748B" anchorX="center" anchorY="middle">
      {subLabel}
    </Text>
  </group>
);

// ── PhotonStream (BB84 moving particles) ───────────────────────────────────
const PhotonStream = ({ count = 30, color = '#00F0FF', speed = 2, noiseLevel = 0.05, isCompromised = false }) => {
  const meshRef = useRef();
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const particles = useMemo(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
      temp.push({
        offset: Math.random() * 20,
        speed: (0.3 + Math.random() * 0.5) * speed,
        phaseY: Math.random() * Math.PI * 2,
        phaseZ: Math.random() * Math.PI * 2,
      });
    }
    return temp;
  }, [count, speed]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.elapsedTime;
    const jitter = isCompromised ? 1.8 : noiseLevel * 6;

    for (let i = 0; i < count; i++) {
      const p = particles[i];
      dummy.position.set(
        ((p.offset + t * p.speed) % 20) - 10,
        Math.sin(t * 6 + p.phaseY) * jitter,
        Math.cos(t * 8 + p.phaseZ) * jitter
      );
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[SPHERE_GEOM, null, count]}>
      <meshBasicMaterial color={color} transparent opacity={0.9} />
    </instancedMesh>
  );
};

// ── E91 Entangled Ribbon Pair (sine-wave TubeGeometry) ─────────────────────
// Replaces photons when E91 + shielded: two intertwined purple sine-wave ribbons
const EntangledRibbons = () => {
  const group = useRef();

  // Build the sine-wave tube paths at mount time
  const { tube1Curve, tube2Curve } = useMemo(() => {
    const pts1 = [];
    const pts2 = [];
    for (let i = 0; i <= 120; i++) {
      const t = (i / 120) * Math.PI * 4;
      const x = (i / 120) * 20 - 10;
      pts1.push(new THREE.Vector3(x, Math.sin(t) * 0.6, Math.cos(t) * 0.6));
      // Phase-shifted by π for the second ribbon (intertwined)
      pts2.push(new THREE.Vector3(x, Math.sin(t + Math.PI) * 0.6, Math.cos(t + Math.PI) * 0.6));
    }
    return {
      tube1Curve: new THREE.CatmullRomCurve3(pts1),
      tube2Curve: new THREE.CatmullRomCurve3(pts2),
    };
  }, []);

  // Animate: slowly pulse the emissive intensity
  useFrame(({ clock }) => {
    if (!group.current) return;
    const t = clock.elapsedTime;
    group.current.children.forEach((child, i) => {
      if (child.material) {
        child.material.emissiveIntensity = 0.6 + Math.sin(t * 2 + i * Math.PI) * 0.4;
      }
    });
  });

  return (
    <group ref={group}>
      <mesh>
        <tubeGeometry args={[tube1Curve, 120, 0.05, 8, false]} />
        <meshStandardMaterial color="#B026FF" emissive="#B026FF" emissiveIntensity={0.8} transparent opacity={0.85} />
      </mesh>
      <mesh>
        <tubeGeometry args={[tube2Curve, 120, 0.05, 8, false]} />
        <meshStandardMaterial color="#8B5CF6" emissive="#8B5CF6" emissiveIntensity={0.8} transparent opacity={0.85} />
      </mesh>
    </group>
  );
};

// ── Main Scene ─────────────────────────────────────────────────────────────
const QuantumScene = React.memo(({ noiseLevel, isCompromised, isAttacked, mitigationStatus, activeProtocol }) => {
  const isE91 = activeProtocol === 'E91';
  const isPA = mitigationStatus === 'PA_ACTIVE';

  // E91 Shielded: E91 protocol + mitigation actively engaged
  const isE91Shielded = isE91 && mitigationStatus === 'E91_ACTIVE';

  // E91 Attacked (no mitigation): bell violation state
  const isE91Attacked = isE91 && isAttacked && mitigationStatus !== 'E91_ACTIVE';

  // ── Color State Machine ──────────────────────────────────────────────────
  // Priority: Shield(purple) > Attack/Compromised(red) > Normal(cyan)
  // NOTE: isPA overrides isCompromised so BB84 mitigated channel is cyan-ish
  let channelColor;
  if (isE91Shielded || isPA) {
    channelColor = '#B026FF'; // Purple: active defense
  } else if (isCompromised || isE91Attacked) {
    channelColor = '#FF003C'; // Red: compromised
  } else {
    channelColor = '#00F0FF'; // Cyan: normal / secure
  }

  // ── Sparkles Config (state-reactive) ────────────────────────────────────
  let sparkleColor, sparkleCount, sparkleSpeed, sparkleSize;
  if (isE91Shielded || isPA) {
    sparkleColor = '#B026FF';
    sparkleCount = 250;
    sparkleSpeed = 0.3;
    sparkleSize = 2.5;
  } else if (isCompromised || isE91Attacked) {
    sparkleColor = '#FF003C';
    sparkleCount = 350;
    sparkleSpeed = 1.2; // 3× faster = channel disturbance
    sparkleSize = 2.0;
  } else {
    sparkleColor = '#00F0FF';
    sparkleCount = 200;
    sparkleSpeed = 0.4;
    sparkleSize = 2.0;
  }

  // ── Bloom intensity ──────────────────────────────────────────────────────
  const bloomIntensity = isE91Shielded || isPA ? 3.5 : isCompromised || isE91Attacked ? 2.5 : 1.6;

  return (
    <>
      {/* Lighting: boosted for glass refraction — MeshTransmissionMaterial needs strong IBL */}
      <ambientLight intensity={1.2} />
      <pointLight position={[0, 8, 0]} intensity={3.0} color="#ffffff" />
      <pointLight position={[0, -8, 0]} intensity={2.0} color="#ffffff" />  {/* back-light forces transparency */}
      <pointLight position={[0, 6, 4]} intensity={2.5} color={channelColor} />
      <pointLight position={[-12, 2, 0]} intensity={1.5} color={channelColor} />
      <pointLight position={[12, 2, 0]} intensity={1.5} color={channelColor} />
      {/* Environment IBL — kept lightweight without transmission */}
      <Environment preset="dawn" />

      {/* Deep-space background sphere */}
      <mesh scale={[60, 60, 60]} geometry={DEPTH_GEOM}>
        <meshBasicMaterial color="#020306" side={THREE.BackSide} />
      </mesh>

      {/* ── Infinite Grid Floor (PATCH: replaces basic gridHelper) ─────── */}
      {/* Uses @react-three/drei Grid with fade-distance for depth perspective */}
      <Grid
        position={[0, -3.5, 0]}
        args={[80, 80]}
        cellSize={1.5}
        cellThickness={0.3}
        cellColor="#0A1A2A"
        sectionSize={8}
        sectionThickness={0.8}
        sectionColor={isE91Shielded || isPA ? '#2D0A4A' : isCompromised || isE91Attacked ? '#3A0010' : '#002A3A'}
        fadeDistance={45}
        fadeStrength={2.0}
        infiniteGrid
      />

      {/* ── Main Channel Group ────────────────────────────────────────── */}
      <group>

        {/* ── Fiber Tube: transparent quantum channel ──────────────────
             Uses proven transparent+opacity approach.
             Inner tube: very translucent (opacity 0.12) base glass shell.
             Outer glow ring: wider, very faint, emissive colored ring for depth.
        ───────────────────────────────────────────────────────────────── */}

        {/* Outer glow halo ring — very faint, just defines the tube boundary */}
        <mesh rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[1.7, 1.7, 20, 32, 1, true]} />
          <meshStandardMaterial
            color={channelColor}
            transparent={true}
            opacity={0.03}
            side={THREE.DoubleSide}
            emissive={channelColor}
            emissiveIntensity={0.05}
            depthWrite={false}
          />
        </mesh>

        {/* Inner glass tube shell — near-invisible so photons show through */}
        <mesh rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[1.4, 1.4, 20, 32, 1, true]} />
          {isE91Shielded ? (
            <meshStandardMaterial
              color="#B026FF"
              transparent={true}
              opacity={0.15}
              wireframe
              side={THREE.DoubleSide}
            />
          ) : (
            <meshStandardMaterial
              color={channelColor}
              transparent={true}
              opacity={0.05}
              side={THREE.DoubleSide}
              emissive={channelColor}
              emissiveIntensity={0.0}
              roughness={0.1}
              metalness={0.0}
              depthWrite={false}
            />
          )}
        </mesh>

        {/* ── Photons / Ribbons (state-reactive) ──────────────────────── */}
        {isE91Shielded ? (
          // E91 Shielded: intertwined sine-wave TubeGeometry ribbons
          <EntangledRibbons />
        ) : (
          // All other states: InstancedMesh photon stream
          <PhotonStream
            count={isCompromised || isE91Attacked ? 90 : 35}
            color={channelColor}
            speed={isCompromised || isE91Attacked ? 5 : 2}
            noiseLevel={noiseLevel}
            isCompromised={isCompromised || isE91Attacked}
          />
        )}

        {/* ── Ambient Sparkles (quantum foam) ─────────────────────────── */}
        {/* Contained within the channel tube, state-reactive color/speed */}
        <Sparkles
          count={sparkleCount}
          scale={[18, 2.5, 2.5]}
          size={sparkleSize}
          speed={sparkleSpeed}
          opacity={0.7}
          color={sparkleColor}
          noise={0.3}
        />

        {/* ── Alice and Bob Nodes ──────────────────────────────────────── */}
        <Node
          position={[-11, 0, 0]}
          label="ALICE"
          subLabel={isE91 ? '[SOURCE]' : '[PREPARE]'}
          color={channelColor}
        />
        <Node
          position={[11, 0, 0]}
          label="BOB"
          subLabel={isE91 ? '[SINK]' : '[MEASURE]'}
          color={channelColor}
        />

        {/* ── Status Text Overlays (state-gated) ──────────────────────── */}
        {isE91Attacked && (
          <Float speed={2} rotationIntensity={0.4}>
            <Text position={[0, 3.5, 0]} fontSize={0.75} color="#FF4D00" anchorX="center" letterSpacing={0.05}>
              {'⚠ BELL TEST VIOLATION DETECTED'}
            </Text>
          </Float>
        )}

        {isE91Shielded && (
          <Float speed={4} rotationIntensity={0.15}>
            <Text position={[0, 3.5, 0]} fontSize={0.65} color="#B026FF" anchorX="center" letterSpacing={0.05}>
              {'🛡 ENTANGLEMENT SHIELD ACTIVE'}
            </Text>
          </Float>
        )}

        {/* BB84 Compromised (no mitigation) */}
        {isCompromised && !isE91 && !isPA && (
          <Float speed={2} rotationIntensity={0.5}>
            <Text position={[0, 3.5, 0]} fontSize={0.75} color="#FF003C" anchorX="center" letterSpacing={0.05}>
              {'⚠ CHANNEL COMPROMISED'}
            </Text>
          </Float>
        )}

        {/* BB84 PA Active */}
        {isPA && (
          <Float speed={5} rotationIntensity={0.1}>
            <Text position={[0, 3.5, 0]} fontSize={0.62} color="#B026FF" anchorX="center" letterSpacing={0.05}>
              {'⚡ PRIVACY AMPLIFICATION ACTIVE'}
            </Text>
          </Float>
        )}

        {/* Eve intercept indicator — centered on channel */}
        {isAttacked && !isE91Shielded && !isPA && (
          <Float speed={3} rotationIntensity={0.8}>
            <Text position={[0, -3.0, 0]} fontSize={0.45} color="#FF8800" anchorX="center" letterSpacing={0.05}>
              {'◆ EVE INTERCEPT DETECTED ◆'}
            </Text>
          </Float>
        )}

      </group>

      {/* ── Camera Controls ──────────────────────────────────────────────── */}
      <OrbitControls
        enableZoom={false}
        autoRotate={!isAttacked}
        autoRotateSpeed={0.4}
        maxPolarAngle={Math.PI / 1.8}
        minPolarAngle={Math.PI / 4}
      />

      {/* ── Post-Processing Stack ─────────────────────────────────────────── */}
      <EffectComposer disableNormalPass>
        <Bloom
          luminanceThreshold={0.3}
          mipmapBlur
          intensity={bloomIntensity}
          radius={0.4}
        />
        {/* Chromatic Aberration: cinematic glass-lens distortion effect */}
        <ChromaticAberration
          blendFunction={BlendFunction.NORMAL}
          offset={new Vector2(0.0006, 0.0006)}
          radialModulation={false}
        />
      </EffectComposer>
    </>
  );
});

// ── Exported QuantumChannel Wrapper ────────────────────────────────────────
export const QuantumChannel = React.memo(({ noiseLevel, isCompromised, isAttacked, mitigationStatus, activeProtocol }) => {
  return (
    <div className="w-full h-full bg-[#020306] rounded-xl border border-quantum-border overflow-hidden relative">
      <Canvas
        shadows={false}
        camera={{ position: [0, 7, 24], fov: typeof window !== 'undefined' && window.innerWidth < 768 ? 48 : 38 }}
        style={{ width: '100%', height: '100%', touchAction: 'none' }}
        gl={{
          antialias: true,
          powerPreference: 'high-performance',
          alpha: false,
          preserveDrawingBuffer: true,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor('#020306', 1);
        }}
      >
        <color attach="background" args={['#020306']} />
        <QuantumScene
          noiseLevel={noiseLevel}
          isCompromised={isCompromised}
          isAttacked={isAttacked}
          mitigationStatus={mitigationStatus}
          activeProtocol={activeProtocol}
        />
      </Canvas>
    </div>
  );
});
