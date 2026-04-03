import React, { useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Float, Html } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { useNavigate } from 'react-router-dom';

const NodeItem = ({ 
  position, 
  title, 
  description, 
  route, 
  color, 
  wireframe = false, 
  children 
}) => {
  const [hovered, setHovered] = useState(false);
  const navigate = useNavigate();

  return (
    <Float speed={2} rotationIntensity={1.5} floatIntensity={1.5}>
      <group position={position}>
        <mesh
          onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
          onPointerOut={(e) => { e.stopPropagation(); setHovered(false); document.body.style.cursor = 'auto'; }}
          onClick={(e) => { e.stopPropagation(); document.body.style.cursor = 'auto'; navigate(route); }}
          scale={hovered ? 1.2 : 1}
        >
          {children}
          <meshStandardMaterial 
            color={color} 
            emissive={color} 
            emissiveIntensity={2} 
            wireframe={wireframe} 
            toneMapped={false}
          />
        </mesh>
        
        {hovered && (
          <Html position={[1.5, 0, 0]} style={{ pointerEvents: 'none' }} zIndexRange={[100, 0]}>
            <div className="glass-panel p-5 rounded-xl border border-[#1A2639] w-64 translate-x-4 pointer-events-auto bg-[#030508]/80 backdrop-blur-md shadow-2xl animate-in fade-in slide-in-from-left-4 duration-300">
              <h3 className="text-white font-sans text-lg tracking-widest uppercase mb-2 drop-shadow-md border-b border-[#1A2639] pb-2">{title}</h3>
              <p className="text-[#64748B] font-mono text-xs leading-relaxed mb-4 mt-2">{description}</p>
              <div 
                className="text-neon-cyan font-mono text-[10px] uppercase tracking-[0.2em] font-bold w-max glow-cyan cursor-pointer transition-colors hover:text-white" 
                onClick={(e) => { e.stopPropagation(); document.body.style.cursor = 'auto'; navigate(route); }}
              >
                SYSTEM OVERRIDE <span className="ml-1 opacity-70">-&gt;</span>
              </div>
            </div>
          </Html>
        )}
      </group>
    </Float>
  );
};

const Home = () => {
  return (
    <div className="relative w-full h-full overflow-hidden bg-[#030508]">
      {/* Decorative background gradient */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] bg-[#00F0FF]/5 rounded-full blur-[150px] pointer-events-none" />
      
      {/* 3D React Three Fiber Canvas */}
      <Canvas camera={{ position: [0, 0, 16], fov: 45 }}>
        <color attach="background" args={['#030508']} />
        
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1.5} color="#ffffff" />
        
        {/* Node 1: QKD Simulation */}
        <NodeItem 
          position={[-4, 0, 0]} 
          title="QKD Simulation" 
          description="Live fiber optic data stream intercept via real-time Quantum Bit Error Rate telemetry."
          route="/sim"
          color="#00F0FF"
        >
          <sphereGeometry args={[1.2, 32, 32]} />
        </NodeItem>

        {/* Node 2: ML Diagnostics */}
        <NodeItem 
          position={[3, 0, 0]} 
          title="ML Diagnostics" 
          description="Deep learning diagnostic matrix mapping real-time QBER anomalies to intercept vectors."
          route="/ml"
          color="#FF003C"
          wireframe={true}
        >
          <icosahedronGeometry args={[1.5, 1]} />
        </NodeItem>

        {/* Node 3: Concepts Library */}
        <NodeItem 
          position={[10, 0, 0]} 
          title="Concepts Library" 
          description="Interactive cryptographic theory, No-Cloning theorem breakdowns, and physics simulation."
          route="/concepts"
          color="#B026FF"
        >
          <torusKnotGeometry args={[0.9, 0.3, 100, 16]} />
        </NodeItem>

        <EffectComposer disableNormalPass>
          <Bloom 
            luminanceThreshold={0.2} 
            luminanceSmoothing={0.9} 
            intensity={1.5} 
            mipmapBlur 
          />
        </EffectComposer>
      </Canvas>

      {/* Foreground UI Layer (HTML Overlay) */}
      <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-10 z-10">
        
        {/* Top-Left Branding */}
        <div className="flex flex-col items-start gap-1">
          <h1 className="text-5xl font-sans text-white tracking-widest uppercase drop-shadow-lg">
            QUANTUM<span className="text-neon-cyan glow-cyan">CIPHERSIM</span>
          </h1>
          <p className="text-neon-cyan font-mono mt-2 tracking-widest text-sm uppercase glow-cyan">
            Next-Generation ML QKD Security Operations Center
          </p>
          <div className="text-neon-cyan border border-neon-cyan px-3 py-1 mt-4 inline-block font-mono text-xs tracking-widest bg-neon-cyan/10">
            [ SYSTEM ONLINE & SECURE ]
          </div>
        </div>

        {/* Bottom-Left Information Panel */}
        <div className="glass-panel w-[400px] pointer-events-auto rounded-xl border border-[#1A2639] p-6 bg-[#0B101A]/80 shadow-2xl backdrop-blur-md">
          <h2 className="text-[#64748B] font-mono text-xs uppercase tracking-[0.2em] border-b border-[#1A2639] pb-3 mb-4">
            Initialization Sequence
          </h2>
          <p className="text-[#94A3B8] font-sans text-sm leading-relaxed tracking-wide">
            Welcome to the QuantumCipherSim SOC. This terminal provides real-time monitoring of BB84 quantum key distribution channels. Select a node to initiate simulation parameters, access the machine learning anomaly detection matrix, or review foundational cryptographic concepts.
          </p>
        </div>

      </div>
    </div>
  );
};

export default Home;
