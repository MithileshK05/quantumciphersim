import React, { useState, useEffect } from 'react';
import { ArrowUp, ArrowRight, ArrowUpRight, ArrowDownRight, ShieldAlert, Cpu, BookOpen, Binary } from 'lucide-react';

const ConceptsLibrary = () => {
  // Simulator State
  const [aliceBit, setAliceBit] = useState(0); // 0 or 1
  const [aliceBasis, setAliceBasis] = useState('+'); // '+' or 'x'
  const [bobBasis, setBobBasis] = useState('+'); // '+' or 'x'
  const [evePresent, setEvePresent] = useState(false);
  
  // Results State
  const [bobMeasurement, setBobMeasurement] = useState(0);
  const [keyStatus, setKeyStatus] = useState('Kept');
  const [errorDetected, setErrorDetected] = useState(false);
  const [eveMeasurement, setEveMeasurement] = useState(null);
  const [eveBasisChoice, setEveBasisChoice] = useState(null);

  // Math/Logic Engine for Photon Transmission
  useEffect(() => {
    let currentPhotonBit = aliceBit;
    let currentPhotonBasis = aliceBasis;

    let eveInterceptedBit = null;
    let randomEveBasis = null;

    // 1. Eve's Intercept
    if (evePresent) {
      // Eve guesses a random basis (pseudo-random for simulator consistency, let's base it on time or just Math.random)
      randomEveBasis = Math.random() > 0.5 ? '+' : 'x';
      setEveBasisChoice(randomEveBasis);

      if (randomEveBasis === currentPhotonBasis) {
        eveInterceptedBit = currentPhotonBit;
      } else {
        // Basis mismatch, photon state collapses to Eve's basis. Eve gets random bit.
        eveInterceptedBit = Math.random() > 0.5 ? 1 : 0;
        currentPhotonBit = eveInterceptedBit;
        currentPhotonBasis = randomEveBasis; // Photon is permanently altered!
      }
      setEveMeasurement(eveInterceptedBit);
    } else {
      setEveBasisChoice(null);
      setEveMeasurement(null);
    }

    // 2. Bob's Measurement
    let finalBobBit = null;
    if (bobBasis === currentPhotonBasis) {
      finalBobBit = currentPhotonBit;
    } else {
      // Bob chose wrong basis for whatever the current photon state is
      finalBobBit = Math.random() > 0.5 ? 1 : 0;
    }

    setBobMeasurement(finalBobBit);

    // 3. Sifting & Error Checking
    if (aliceBasis === bobBasis) {
      setKeyStatus('Kept');
      // If Eve altered the photon, Bob might measure a different bit even though bases match!
      if (finalBobBit !== aliceBit) {
        setErrorDetected(true);
      } else {
        setErrorDetected(false); // Eve might have gotten lucky and collapsed it back to original, or no Eve
      }
    } else {
      setKeyStatus('Discarded');
      setErrorDetected(false); // Errors are only checked on kept bits
    }

  }, [aliceBit, aliceBasis, bobBasis, evePresent]);


  // Visualization Helper
  const getPhotonIcon = (bit, basis, size = 48, className = "") => {
    if (basis === '+') {
      return bit === 0 ? <ArrowUp size={size} className={className} /> : <ArrowRight size={size} className={className} />;
    } else {
      return bit === 0 ? <ArrowUpRight size={size} className={className} /> : <ArrowDownRight size={size} className={className} />;
    }
  };

  return (
    <div className="h-full w-full bg-[#030508] p-6 overflow-y-auto custom-scrollbar">
      
      {/* Header Area */}
      <div className="mb-8">
        <h1 className="text-3xl font-sans tracking-wide glow-cyan text-neon-cyan uppercase flex items-center gap-3">
          <BookOpen className="text-neon-cyan" /> Interactive Concepts Library
        </h1>
        <p className="text-[#64748B] font-mono mt-2 uppercase tracking-widest text-sm">BB84 Simulation & Security Cryptography</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pb-12">
        
        {/* Left Column: BB84 Interactive Simulator */}
        <div className="glass-panel p-6 rounded-xl border border-[#1A2639] flex flex-col gap-6">
          <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 font-bold flex items-center gap-2">
            <Cpu size={16} /> BB84 Interactive Simulator
          </h2>

          <p className="text-sm font-mono text-[#94A3B8] leading-relaxed">
            Configure the quantum transmission parameters below. Observe how state collapse guarantees cryptographic security.
          </p>

          <div className="flex flex-col gap-6 bg-[#0B101A] p-5 rounded border border-[#1A2639]">
            
            {/* Alice Controls */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest">Alice's Bit</label>
                <div className="flex gap-2 bg-[#0A0E17] p-1 rounded border border-[#1A2639]">
                  <button onClick={() => setAliceBit(0)} className={`flex-1 py-2 font-mono text-sm rounded transition-all ${aliceBit === 0 ? 'bg-neon-cyan text-black glow-cyan font-bold' : 'text-[#64748B] hover:text-white'}`}>0</button>
                  <button onClick={() => setAliceBit(1)} className={`flex-1 py-2 font-mono text-sm rounded transition-all ${aliceBit === 1 ? 'bg-neon-cyan text-black glow-cyan font-bold' : 'text-[#64748B] hover:text-white'}`}>1</button>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest">Alice's Basis</label>
                <div className="flex gap-2 bg-[#0A0E17] p-1 rounded border border-[#1A2639]">
                  <button onClick={() => setAliceBasis('+')} className={`flex-1 py-2 font-mono text-sm rounded transition-all ${aliceBasis === '+' ? 'bg-neon-cyan text-black glow-cyan font-bold' : 'text-[#64748B] hover:text-white'}`}>Rect (+)</button>
                  <button onClick={() => setAliceBasis('x')} className={`flex-1 py-2 font-mono text-sm rounded transition-all ${aliceBasis === 'x' ? 'bg-neon-cyan text-black glow-cyan font-bold' : 'text-[#64748B] hover:text-white'}`}>Diag (x)</button>
                </div>
              </div>
            </div>

            {/* Photon Visualization */}
            <div className="flex flex-col items-center justify-center py-6 border-y border-[#1A2639] border-dashed relative">
                <span className="absolute top-2 left-2 text-[9px] uppercase font-sans text-[#64748B] tracking-[0.2em]">Photon Flight Path</span>
                <div className="flex items-center gap-12 w-full justify-center">
                    
                    {/* Alice's Photon */}
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-16 h-16 rounded-full border border-neon-cyan/50 bg-neon-cyan/10 flex items-center justify-center text-neon-cyan glow-cyan shadow-[inset_0_0_15px_rgba(0,240,255,0.2)]">
                        {getPhotonIcon(aliceBit, aliceBasis, 32)}
                      </div>
                      <span className="text-[10px] uppercase font-mono text-[#64748B]">Alice State</span>
                    </div>

                    {/* Channel / Eve */}
                    <div className="flex-1 flex items-center justify-center relative">
                      <div className="w-full h-[2px] bg-gradient-to-r from-neon-cyan via-[#1A2639] to-[#0B101A] relative shadow-[0_0_10px_#00F0FF]">
                         {evePresent && (
                           <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center">
                              <ShieldAlert className="text-neon-red drop-shadow-[0_0_8px_#FF003C] bg-[#030508] p-1 rounded-full border border-neon-red" size={32} />
                              <div className="mt-2 text-[10px] font-mono text-neon-red whitespace-nowrap bg-red-900/40 px-2 py-1 rounded border border-neon-red/50">
                                Eve Guessed: {eveBasisChoice}<br/>
                                Eve Hit: {eveMeasurement}
                              </div>
                           </div>
                         )}
                      </div>
                    </div>

                    {/* Bob's Received Photon (What Bob actually interacts with) */}
                    <div className="flex flex-col items-center gap-2">
                      <div className={`w-16 h-16 rounded-full border flex items-center justify-center transition-all duration-300 ${evePresent && eveBasisChoice !== aliceBasis ? 'border-neon-red/50 bg-neon-red/10 text-neon-red shadow-[inset_0_0_15px_rgba(255,0,60,0.2)]' : 'border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan'}`}>
                        {getPhotonIcon(
                          evePresent ? (eveBasisChoice === aliceBasis ? aliceBit : eveMeasurement) : aliceBit, 
                          evePresent ? (eveBasisChoice === aliceBasis ? aliceBasis : eveBasisChoice) : aliceBasis, 
                          32
                        )}
                      </div>
                      <span className="text-[10px] uppercase font-mono text-[#64748B]">Arriving State</span>
                    </div>
                </div>
            </div>

            {/* Bob Controls */}
            <div className="flex flex-col gap-2">
              <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest">Bob's Measurement Basis</label>
              <div className="flex gap-2 bg-[#0A0E17] p-1 rounded border border-[#1A2639]">
                <button onClick={() => setBobBasis('+')} className={`flex-1 py-2 font-mono text-sm rounded transition-all ${bobBasis === '+' ? 'bg-neon-cyan text-black glow-cyan font-bold' : 'text-[#64748B] hover:text-white'}`}>Rect (+)</button>
                <button onClick={() => setBobBasis('x')} className={`flex-1 py-2 font-mono text-sm rounded transition-all ${bobBasis === 'x' ? 'bg-neon-cyan text-black glow-cyan font-bold' : 'text-[#64748B] hover:text-white'}`}>Diag (x)</button>
              </div>
            </div>

            {/* Eve Toggle */}
            <div className="mt-2">
              <button 
                onClick={() => setEvePresent(!evePresent)}
                className={`w-full py-3 rounded font-mono text-sm tracking-widest uppercase transition-all duration-300 font-bold border ${evePresent ? 'bg-neon-red/20 text-neon-red border-neon-red glow-red' : 'bg-[#030508] text-[#64748B] border-[#1A2639] hover:border-neon-red/50 hover:text-neon-red'}`}
              >
                {evePresent ? "EVE IS INTERCEPTING" : "INJECT EVE"}
              </button>
            </div>
          </div>

          {/* Result Display Area */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
             <div className="glass-panel p-4 rounded border border-[#1A2639] flex flex-col items-center justify-center bg-[#0B101A]">
                <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2 text-center">Bob's Readout</span>
                <span className="text-3xl font-mono text-white font-bold">{bobMeasurement}</span>
             </div>
             
             <div className={`glass-panel p-4 rounded border flex flex-col items-center justify-center transition-all ${keyStatus === 'Kept' ? 'border-neon-cyan/50 bg-[#00F0FF]/5' : 'border-[#1A2639] bg-[#030508]'}`}>
                <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2 text-center">Key Status</span>
                <span className={`text-xl font-mono font-bold uppercase tracking-widest ${keyStatus === 'Kept' ? 'text-neon-cyan glow-cyan' : 'text-[#64748B]'}`}>{keyStatus}</span>
             </div>

             <div className={`glass-panel p-4 rounded border flex flex-col items-center justify-center transition-all ${errorDetected ? 'border-neon-red bg-neon-red/10' : 'border-[#1A2639] bg-[#030508]'}`}>
                <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2 text-center">Protocol Error</span>
                <span className={`text-xl font-mono font-bold uppercase tracking-widest ${errorDetected ? 'text-neon-red drop-shadow-[0_0_8px_#FF003C]' : 'text-green-500'}`}>{errorDetected ? "DETECTED!" : "NONE"}</span>
             </div>
          </div>

        </div>

        {/* Right Column: Educational Content */}
        <div className="glass-panel p-8 rounded-xl border border-[#1A2639] flex flex-col gap-8 h-full shadow-lg">
           
           <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 font-bold flex items-center gap-2 mb-2">
            <Binary size={16} /> Quantum Physics Theory
           </h2>

           <section className="font-sans">
              <h3 className="text-xl text-white tracking-wide mb-3 uppercase">The No-Cloning Theorem</h3>
              <p className="text-[#94A3B8] text-sm leading-relaxed font-mono">
                At the heart of the BB84 protocol lies the <span className="text-neon-cyan">No-Cloning Theorem</span> of quantum mechanics. It states that it is physically impossible to create an identical copy of an unknown quantum state. 
                <br/><br/>
                If Eve (the eavesdropper) wants to read the key being transmitted, she cannot simply clone the photon and read the copy later. She <strong>must</strong> interact with the original photon in transit. 
                Because quantum states collapse when measured, her interaction unavoidably alters the physical state of the photon, leaving a permanent fingerprint.
              </p>
           </section>

           <section className="font-sans">
              <h3 className="text-xl text-white tracking-wide mb-3 uppercase flex items-center gap-2">
                The Intercept-Resend Attack
              </h3>
              <p className="text-[#94A3B8] text-sm leading-relaxed font-mono">
                When Eve intercepts the channel, she must guess the measurement basis (Rectilinear <code className="text-neon-cyan bg-[#0B101A] px-1">+</code > or Diagonal <code className="text-neon-cyan bg-[#0B101A] px-1">x</code>). She has a 50% chance of guessing wrong.
                <br/><br/>
                If she guesses wrong, she permanently corrupts the photon, collapsing it into her incorrect basis. When Bob receives this corrupted photon and measures it in Alice's *correct* basis, the physics forces a purely random outcome (50% chance of an error).
                <br/><br/>
                Mathematically: <code className="text-neon-red font-bold">0.5 * 0.5 = 0.25</code>. An active intercept-resend attack generates a guaranteed <strong>25% Quantum Bit Error Rate (QBER)</strong> overhead in the sifted key.
              </p>
           </section>

           <section className="font-sans mt-auto border-t border-[#1A2639] pt-6">
              <h3 className="text-xl text-neon-cyan glow-cyan tracking-wide mb-3 uppercase">Machine Learning Side-Channels</h3>
              <p className="text-[#94A3B8] text-sm leading-relaxed font-mono">
                In real-world fiber optics, physical noise (depolarization, dark counts) also causes QBER. A sophisticated Eve can hide her 25% error footprint by attempting to exploit noisy channels or performing partial state attacks.
                <br/><br/>
                This is where our dashboard's <span className="text-white font-bold tracking-widest border-b border-neon-red">MACHINE LEARNING</span> architecture takes over. 
                By consuming the high-dimensional telemetry matrix (`Raw QBER`, `Channel Noise`, and `Sifted Key Length`), the ML models (Random Forest, SVM) isolate the statistical variance of the physical noise out of the string, exposing the distinct mathematical footprint of Eve's measurement errors with 98%+ confidence.
              </p>
           </section>
        </div>

      </div>
    </div>
  );
};

export default ConceptsLibrary;
