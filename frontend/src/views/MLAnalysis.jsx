import React, { useState, useEffect } from 'react';
import { useQKDMetrics } from '../hooks/useQKDMetrics';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ArrowRight, Database, Cpu, Activity, ShieldAlert, ShieldCheck, Atom, Zap, GitMerge, Link } from 'lucide-react';
import { useSimulation } from '../context/SimulationContext';
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const initialModelsConfig = [
  { id: 'gradient_boosting', name: 'Gradient Boosting', acc: 1.0000, prec: 1.0000, rec: 1.0000, f1: 1.0000 },
  { id: 'random_forest', name: 'Random Forest', acc: 1.0000, prec: 1.0000, rec: 1.0000, f1: 1.0000 },
  { id: 'logistic_regression', name: 'Logistic Regression', acc: 0.9981, prec: 0.9989, rec: 0.9972, f1: 0.9980 },
  { id: 'svm', name: 'Support Vector Machine', acc: 0.9979, prec: 0.9987, rec: 0.9971, f1: 0.9979 }
];

const MLAnalysis = () => {
  const [selectedModelId, setSelectedModelId] = useState('gradient_boosting');
  const [modelsData, setModelsData] = useState(initialModelsConfig);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await axios.get(`${BASE_URL}/models`);
        if (res.data && res.data.models) {
          const updated = initialModelsConfig.map(mc => {
            const found = res.data.models.find(m => m.model_type === mc.id);
            if (found) {
              const acc = found.accuracy;
              const rec = found.recall_attack ?? acc;
              const prec = found.precision ?? acc;
              const f1 = (2 * prec * rec) / (prec + rec || 1);
              return { ...mc, acc, prec, rec, f1 };
            }
            return mc;
          });
          setModelsData(updated);
        }
      } catch (err) {
        console.error("Failed to fetch models from backend:", err);
      }
    };
    fetchModels();
  }, []);

  const { 
    isAttacked, setIsAttacked,
    noiseLevel,
    autoMitigate,
    activeProtocol
  } = useSimulation(); // Global simulation state synced with SimView
  
  // Sync with SimView's hook signature for exact backend state match
  const { data: metrics } = useQKDMetrics(
    noiseLevel, 
    isAttacked ? 1.0 : 0.0, 
    selectedModelId, 
    autoMitigate, 
    activeProtocol
  );

  const selectedModel = modelsData.find(m => m.id === selectedModelId) || modelsData[0];
  const isE91 = activeProtocol === 'E91';

  // E91-specific Bell inequality metrics derived from live backend QBER
  // Formula: S = 2√2 × (1 − 2×QBER)   [Tsirelson's bound variant]
  // S > 2.0 → quantum entanglement confirmed → channel secure
  // S ≤ 2.0 → classical correlations → eavesdropping detected
  const e91Metrics = React.useMemo(() => {
    const qber = metrics?.qber ?? 0;
    const chshScore        = Math.min(2 * Math.SQRT2 * (1 - 2 * qber), 2 * Math.SQRT2);
    const bellViolation    = Math.max(0, ((chshScore - 2.0) / (2 * Math.SQRT2 - 2.0)) * 100);
    const entanglementFid  = Math.max(0, (1 - 2 * qber) * 100);
    const correlationCoeff = Math.abs(0.7071 * (1 - 2 * qber));
    const isSecure         = chshScore > 2.0;
    return { chshScore, bellViolation, entanglementFid, correlationCoeff, isSecure };
  }, [metrics?.qber]);

  // E91 bar chart data: how strongly the Bell inequality is violated vs classical limit
  const e91BarData = React.useMemo(() => {
    if (isAttacked) {
      // During active interception, entanglement breaks and collapses into classical correlation limits
      const riskValue = 98.5 + (metrics?.qber ?? 0) * 10;
      return [
        { name: 'Classical Limit Risk', value: Math.min(99.9, riskValue), fill: '#FF003C' },
        { name: 'Quantum Bell Violation', value: Math.max(0.1, 100 - Math.min(99.9, riskValue)), fill: '#00F0FF' }
      ];
    } else {
      return [
        { name: 'Classical Limit Risk', value: Math.max(0, 100 - e91Metrics.bellViolation), fill: '#334155' },
        { name: 'Quantum Bell Violation', value: e91Metrics.bellViolation, fill: '#00F0FF' }
      ];
    }
  }, [e91Metrics.bellViolation, isAttacked, metrics?.qber]);

  // Derived threat data for BarChart — updated to perfectly reflect model accuracy and live metrics
  const { threatData, threatLevel, isHighThreat, isMitigated } = React.useMemo(() => {
    const rawThreatLevel    = metrics?.threat_level      || (isAttacked ? 'HIGH' : 'LOW');
    const mitigationStatus  = metrics?.mitigation_status || 'NONE';
    const mitigated = mitigationStatus === 'PA_ACTIVE' || mitigationStatus === 'E91_ACTIVE';
    const modelAcc = selectedModel?.acc ?? 1.0;

    let attackValue, secureValue, attackFill;

    if (isAttacked) {
      if (mitigated) {
        // When attack is ON but auto-mitigation is ON, the threat is successfully neutralized!
        // The channel is restored to a Secure Channel matching the model's accuracy/security metrics.
        secureValue = modelAcc * 100;
        attackValue = 100 - secureValue;
        attackFill  = '#FF9500';
      } else {
        // When attack is ON and auto-mitigation is OFF, the unmitigated attack is detected.
        attackValue = modelAcc * 100;
        secureValue = 100 - attackValue;
        attackFill  = '#FF003C';
      }
    } else {
      // When attack is OFF, channel is secure matching model accuracy
      secureValue = modelAcc * 100;
      attackValue = 100 - secureValue;
      attackFill  = '#FF003C';
    }

    const label = mitigated
      ? `MITIGATED (${mitigationStatus.replace('_', ' ')})`
      : (isAttacked ? 'HIGH THREAT (ATTACK DETECTED)' : 'SECURE (LOW THREAT)');

    return {
      threatData: [
        { name: 'Intercept-Resend Attack', value: attackValue,  fill: attackFill },
        { name: 'Secure Channel',          value: secureValue,  fill: '#00F0FF'  }
      ],
      threatLevel:  label,
      isHighThreat: isAttacked && !mitigated,
      isMitigated:  mitigated
    };
  }, [metrics?.threat_level, metrics?.mitigation_status, isAttacked, selectedModel?.acc]);




  return (
    <div className="h-full w-full bg-[#030508] text-text-main overflow-y-auto custom-scrollbar p-6">
      
      {/* Header Area */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-sans tracking-wide glow-cyan text-neon-cyan uppercase">{isE91 ? 'Quantum Security Analysis' : 'Machine Learning Analysis'}</h1>
        <button 
          onClick={() => setIsAttacked(!isAttacked)}
          className={`px-6 py-2 rounded font-mono text-sm tracking-widest uppercase transition-all duration-300 font-bold border ${isAttacked ? 'bg-neon-red/20 text-neon-red border-neon-red glow-red' : 'bg-transparent text-[#64748B] border-[#1A2639] hover:border-neon-cyan hover:text-neon-cyan'}`}
        >
          {isAttacked ? "SIMULATING ATTACK: ON" : "SIMULATING ATTACK: OFF"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-12">
        
        {/* Left Column — switches between BB84 ML config and E91 Bell Test config */}
        <div className="col-span-1 lg:col-span-4 flex flex-col gap-6">
          <div className="glass-panel p-6 rounded-xl border border-quantum-border flex flex-col gap-6 sticky top-6">

          {isE91 ? (
            /* ── E91 Bell Test Configuration ─────────────────────────────── */
            <>
              <div className="flex items-center gap-3 border-b border-[#1A2639] pb-4">
                <Atom className="text-neon-cyan shrink-0" size={18} />
                <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans font-bold">Bell Test Configuration</h2>
              </div>

              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest pl-1">Protocol</label>
                <div className="w-full bg-[#0B101A] border border-neon-cyan/30 text-neon-cyan p-3 rounded font-mono text-sm tracking-widest text-center shadow-[0_0_10px_rgba(0,240,255,0.1)]">
                  E91 — Ekert 1991
                </div>
              </div>

              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest pl-1">Verification Method</label>
                <div className="w-full bg-[rgba(11,16,26,0.6)] border border-[#1A2639] text-[#94A3B8] p-3 rounded font-mono text-xs">
                  CHSH Inequality Test<br/>
                  <span className="text-neon-cyan">|S| ≤ 2√2 ≈ 2.828</span>
                </div>
              </div>

              <div className="p-5 bg-[rgba(11,16,26,0.6)] border border-[#1A2639] rounded overflow-hidden relative">
                <div className="absolute top-0 left-0 w-1 h-full bg-neon-cyan shadow-[0_0_10px_#00F0FF]"></div>
                <h3 className="text-[11px] uppercase tracking-[0.2em] text-[#64748B] mb-3 font-sans font-bold">Bell Test Profile</h3>
                <div className="font-mono text-sm text-[#94A3B8] leading-loose">
                  <div className="flex justify-between">
                    <span>Quantum Bound:</span>
                    <span className="text-white">2.828</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Security Threshold:</span>
                    <span className="text-white">&gt; 2.000</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Current S value:</span>
                    <span className={e91Metrics.isSecure ? 'text-neon-cyan drop-shadow-[0_0_5px_#00F0FF]' : 'text-neon-red'}>
                      {e91Metrics.chshScore.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex justify-between border-t border-[#1A2639] mt-2 pt-2">
                    <span className="text-neon-cyan">Status:</span>
                    <span className={`font-bold ${e91Metrics.isSecure ? 'text-neon-cyan drop-shadow-[0_0_5px_#00F0FF]' : 'text-neon-red'}`}>
                      {e91Metrics.isSecure ? 'QUANTUM SECURE' : 'COMPROMISED'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-[10px] font-mono text-[#334155] text-center leading-relaxed border border-[#1A2639] rounded p-3">
                E91 uses entangled photon pairs.<br/>
                Bell test violations prove security<br/>
                <span className="text-neon-cyan/50">without ML inference.</span>
              </div>
            </>
          ) : (
            /* ── BB84 ML Model Configuration ─────────────────────────────── */
            <>
              <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 font-bold">ML Model Configuration</h2>

              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest pl-1">Active Model</label>
                <select
                  value={selectedModelId}
                  onChange={(e) => setSelectedModelId(e.target.value)}
                  className="w-full bg-[#0B101A] border border-[#1A2639] text-text-main p-3 rounded font-mono text-sm focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan transition-colors"
                >
                  {modelsData.map(model => (
                    <option key={model.id} value={model.id}>{model.name}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest pl-1">Training Dataset</label>
                <div className="space-y-4">
                  <select disabled className="w-full bg-[rgba(11,16,26,0.6)] border border-[#1A2639] text-[#64748B] p-3 rounded font-mono text-sm uppercase">
                    <option>Qiskit BB84 Dataset (50,000 runs)</option>
                  </select>
                  <input type="range" disabled value="75" className="quantum-slider opacity-50" />
                </div>
              </div>

              <div className="mt-6 p-5 bg-[rgba(11,16,26,0.6)] border border-[#1A2639] rounded overflow-hidden relative group">
                <div className="absolute top-0 left-0 w-1 h-full bg-neon-cyan shadow-[0_0_10px_#00F0FF]"></div>
                <h3 className="text-[11px] uppercase tracking-[0.2em] text-[#64748B] mb-3 font-sans font-bold">Model Summary Profile</h3>
                <div className="font-mono text-sm text-[#94A3B8] leading-loose">
                  <div className="flex justify-between transition-all duration-300">
                    <span>Accuracy:</span>
                    <span className="text-white">{(selectedModel.acc * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between transition-all duration-300">
                    <span>Precision:</span>
                    <span className="text-white">{selectedModel.prec.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between transition-all duration-300">
                    <span>Recall:</span>
                    <span className="text-white">{selectedModel.rec.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between border-t border-[#1A2639] mt-2 pt-2 transition-all duration-300">
                    <span className="text-neon-cyan">F1-Score:</span>
                    <span className="text-neon-cyan drop-shadow-[0_0_5px_#00F0FF]">{selectedModel.f1.toFixed(4)}</span>
                  </div>
                </div>
              </div>
            </>
          )}

          </div>
        </div>

        {/* Right Column (Analytics) */}
        <div className="col-span-1 lg:col-span-8 flex flex-col gap-8">
          
          {isE91 ? (
            /* ════════════════════════════════════════════════
               E91 BELL TEST PANELS
               ════════════════════════════════════════════════ */
            <>
            {/* E91 Panel 1: Bell Inequality Verification Chart */}
            <div className="glass-panel p-6 rounded-xl border border-quantum-border w-full flex-col flex relative overflow-hidden min-h-[250px]">
              <div className="flex items-center gap-3 border-b border-[#1A2639] pb-4 mb-6">
                <Zap className="text-neon-cyan" size={14} />
                <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans font-bold">Bell Inequality Verification (CHSH)</h2>
                <span className="ml-auto text-[10px] font-mono text-neon-cyan bg-neon-cyan/10 px-2 py-1 rounded tracking-widest">
                  S = {e91Metrics.chshScore.toFixed(4)}
                </span>
              </div>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={e91BarData} layout="vertical" margin={{ top: 10, right: 30, left: 60, bottom: 5 }}>
                    <XAxis type="number" domain={[0, 100]} stroke="#1A2639" tick={{ fill: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" stroke="#1A2639" tick={{ fill: '#E2E8F0', fontFamily: 'JetBrains Mono', fontSize: 11 }} width={180} />
                    <Tooltip
                      cursor={{ fill: '#0B101A' }}
                      contentStyle={{ backgroundColor: '#030508', borderColor: '#1A2639', borderRadius: '4px', color: '#E2E8F0', fontFamily: 'JetBrains Mono' }}
                      formatter={(value) => [`${value.toFixed(2)}%`, 'Strength']}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={32} isAnimationActive={true} animationDuration={500}>
                      {e91BarData.map((entry, index) => (
                        <Cell key={`e91-cell-${index}`} fill={entry.fill}
                          className={entry.name === 'Quantum Bell Violation' ? 'drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]' : ''}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* E91 Panel 2: Quantum Channel Metrics */}
            <div className="glass-panel p-6 rounded-xl border border-quantum-border w-full">
              <div className="flex items-center justify-between border-b border-[#1A2639] pb-4 mb-6">
                <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans font-bold">Quantum Entanglement Metrics</h2>
                <span className="text-[10px] uppercase font-mono text-neon-cyan tracking-widest bg-neon-cyan/10 px-2 py-1 rounded">Live Measurement</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass-panel bg-[#0B101A] border-neon-cyan/30 border rounded p-4 flex flex-col justify-between shadow-[0_0_10px_rgba(0,240,255,0.08)]">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-neon-cyan mb-2">CHSH Score (S)</span>
                  <span className="text-2xl font-mono text-neon-cyan font-bold drop-shadow-[0_0_5px_#00F0FF]">{e91Metrics.chshScore.toFixed(3)}</span>
                </div>
                <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">Bell Violation</span>
                  <span className="text-2xl font-mono text-neon-cyan font-bold">{e91Metrics.bellViolation.toFixed(1)}%</span>
                </div>
                <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">Entangle. Fidelity</span>
                  <span className="text-2xl font-mono text-neon-cyan font-bold">{e91Metrics.entanglementFid.toFixed(1)}%</span>
                </div>
                <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">Corr. Coefficient</span>
                  <span className="text-2xl font-mono text-neon-cyan font-bold">{e91Metrics.correlationCoeff.toFixed(4)}</span>
                </div>
              </div>
            </div>

            {/* E91 Panel 3: Entanglement Verification Trace */}
            <div className="glass-panel p-6 rounded-xl border border-quantum-border w-full overflow-hidden">
              <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 mb-6 font-bold">Entanglement Verification Trace</h2>
              <div className="flex flex-col xl:flex-row items-center justify-between w-full gap-4 overflow-x-auto pb-6">

                <div className="flex flex-col items-center justify-center p-5 bg-[#0B101A] border border-[#1A2639] rounded-lg min-w-[160px]">
                  <Atom className="text-neon-cyan mb-3" size={20} />
                  <span className="text-[9px] text-[#64748B] font-sans uppercase tracking-[0.2em] mb-2 text-center">Entangled Pair Gen.</span>
                  <span className="text-xs font-mono text-white text-center">EPR Source<br/>|Φ⁺⟩ state</span>
                </div>

                <ArrowRight className="text-[#334155] shrink-0" size={24} />

                <div className="flex flex-col items-center justify-center p-5 bg-[#0B101A] border border-[#1A2639] rounded-lg min-w-[160px]">
                  <Link className="text-[#64748B] mb-3" size={20} />
                  <span className="text-[9px] text-[#64748B] font-sans uppercase tracking-[0.2em] mb-2 text-center">Corr. Measurement</span>
                  <span className="text-xs font-mono text-white text-center">QBER: {(metrics?.qber ?? 0).toFixed(3)}<br/>3-basis sampling</span>
                </div>

                <ArrowRight className="text-[#334155] shrink-0" size={24} />

                <div className="flex flex-col items-center justify-center p-5 bg-[#0A0E17] border border-neon-cyan/30 shadow-[0_0_10px_rgba(0,240,255,0.1)] rounded-lg min-w-[190px]">
                  <GitMerge className="text-neon-cyan mb-3" size={20} />
                  <span className="text-[9px] text-[#00F0FF] font-sans uppercase tracking-[0.2em] mb-2 text-center">CHSH Calculation</span>
                  <span className="text-xs font-mono text-neon-cyan text-center font-bold">S = 2√2×(1−2×QBER)<br/>= {e91Metrics.chshScore.toFixed(4)}</span>
                </div>

                <ArrowRight className="text-neon-cyan drop-shadow-[0_0_8px_rgba(0,240,255,0.6)] shrink-0" size={24} />

                <div className={`flex flex-col items-center justify-center p-5 rounded-lg min-w-[160px] relative overflow-hidden transition-all duration-500 border-2 ${e91Metrics.isSecure ? 'bg-[#0B101A] border-neon-cyan shadow-[0_0_15px_rgba(0,240,255,0.2)]' : 'bg-neon-red border-[#FF003C] shadow-[0_0_25px_rgba(255,0,60,0.4)]'}`}>
                  {e91Metrics.isSecure
                    ? <ShieldCheck className="text-neon-cyan mb-2 relative z-10" size={28} />
                    : <ShieldAlert className="text-white mb-2 relative z-10" size={28} />
                  }
                  <span className={`text-[9px] font-sans uppercase tracking-[0.2em] mb-1 relative z-10 ${e91Metrics.isSecure ? 'text-neon-cyan/80' : 'text-white/80'}`}>BELL VERDICT</span>
                  <span className={`text-sm font-mono font-bold tracking-widest relative z-10 text-center ${e91Metrics.isSecure ? 'text-neon-cyan' : 'text-white'}`}>
                    {e91Metrics.isSecure
                      ? <><span>ENTANGLEMENT</span><br/><span>VERIFIED</span></>
                      : <><span>BELL TEST</span><br/><span>FAILED</span></>
                    }
                  </span>
                </div>

              </div>
            </div>
            </>
          ) : (
            /* ════════════════════════════════════════════════
               BB84 ML ANALYSIS PANELS
               ════════════════════════════════════════════════ */
            <>
          {/* Panel 1: REAL-TIME THREAT CLASSIFICATION */}
          <div className="glass-panel p-6 rounded-xl border border-quantum-border w-full flex-col flex relative overflow-hidden min-h-[250px]">
            <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 mb-6 font-bold">Real-Time Threat Classification</h2>
            <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={threatData} layout="vertical" margin={{ top: 10, right: 30, left: 40, bottom: 5 }}>
                      <XAxis type="number" domain={[0, 100]} stroke="#1A2639" tick={{ fill: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" stroke="#1A2639" tick={{ fill: '#E2E8F0', fontFamily: 'JetBrains Mono', fontSize: 12 }} width={200} />
                      <Tooltip 
                        cursor={{fill: '#0B101A'}}
                        contentStyle={{ backgroundColor: '#030508', borderColor: '#1A2639', borderRadius: '4px', color: '#E2E8F0', fontFamily: 'JetBrains Mono' }}
                        formatter={(value) => [`${value.toFixed(2)}%`, 'Probability']}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={32} isAnimationActive={true} animationDuration={500}>
                      {threatData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.fill} 
                            className={
                              entry.name === 'Intercept-Resend Attack' && isHighThreat && !isMitigated
                                ? 'drop-shadow-[0_0_12px_rgba(255,0,60,0.8)]'
                                : entry.name === 'Intercept-Resend Attack' && isMitigated
                                ? 'drop-shadow-[0_0_10px_rgba(255,149,0,0.7)]'
                                : entry.name === 'Secure Channel' && !isHighThreat
                                ? 'drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]'
                                : ''
                            }
                          />
                      ))}
                      </Bar>
                  </BarChart>
                </ResponsiveContainer>
            </div>
          </div>

          {/* Panel 2: LIVE FEATURE INFERENCE MATRIX */}
          <div className="glass-panel p-6 rounded-xl border border-quantum-border w-full">
            <div className="flex items-center justify-between border-b border-[#1A2639] pb-4 mb-6">
                <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans font-bold">Live Feature Inference Matrix</h2>
                <span className="text-[10px] uppercase font-mono text-neon-cyan tracking-widest bg-neon-cyan/10 px-2 py-1 rounded">Polling backend</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               <div className={`glass-panel border rounded p-4 flex flex-col justify-between transition-colors duration-500 ${isHighThreat ? 'bg-red-900/20 border-neon-red shadow-[0_0_15px_rgba(255,0,60,0.2)] text-neon-red glow-red' : 'bg-[#0B101A] border-[#1A2639] text-white'}`}>
                  <span className="text-[10px] uppercase tracking-widest font-sans opacity-70 mb-2">RAW QBER</span>
                  <span className="text-2xl font-mono font-bold">{metrics ? (metrics.qber * 100).toFixed(2) : '0.00'}%</span>
               </div>
               <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between transition-colors duration-500">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">CHANNEL NOISE</span>
                  <span className="text-2xl font-mono text-[#E2E8F0] font-bold">{metrics ? metrics.noise_level.toFixed(3) : '0.000'}</span>
               </div>
               <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between transition-colors duration-500">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">SIFTED KEY</span>
                  <span className="text-2xl font-mono text-neon-cyan font-bold">{metrics ? metrics.sifted_key_length : '0'}</span>
               </div>
               <div className={`glass-panel border rounded p-4 flex flex-col justify-between transition-colors duration-500 ${isHighThreat ? 'bg-red-900/20 border-neon-red shadow-[0_0_15px_rgba(255,0,60,0.2)] text-neon-red glow-red' : 'bg-[#0B101A] border-[#1A2639] text-white'}`}>
                  <span className="text-[10px] uppercase tracking-widest font-sans opacity-70 mb-2">EVE CONTRIB.</span>
                  <span className="text-2xl font-mono font-bold">{metrics ? metrics.eve_contribution.toFixed(4) : '0.0000'}</span>
               </div>
            </div>
          </div>

          {/* Panel 3: ALGORITHMIC DECISION TRACE */}
          <div className="glass-panel p-6 rounded-xl border border-quantum-border w-full overflow-hidden">
            <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 mb-6 font-bold">Algorithmic Decision Trace</h2>
            <div className="flex flex-col xl:flex-row items-center justify-between w-full gap-4 overflow-x-auto pb-6">
              <div className="flex flex-col items-center justify-center p-5 bg-[#0B101A] border border-[#1A2639] rounded-lg min-w-[180px]">
                <Database className="text-[#64748B] mb-3" size={20} />
                <span className="text-[9px] text-[#64748B] font-sans uppercase tracking-[0.2em] mb-2 text-center">Observable Extraction</span>
                <span className="text-xs font-mono text-white text-center">QBER: {(metrics?.qber ?? 0).toFixed(3)}<br/>Noise: {(metrics?.noise_level ?? 0).toFixed(3)}</span>
              </div>
              <ArrowRight className="text-[#334155] shrink-0" size={24} />
              <div className="flex flex-col items-center justify-center p-5 bg-[#0A0E17] border border-neon-cyan/30 shadow-[0_0_10px_rgba(0,240,255,0.1)] rounded-lg min-w-[200px]">
                <Activity className="text-neon-cyan mb-3" size={20} />
                <span className="text-[9px] text-[#00F0FF] font-sans uppercase tracking-[0.2em] mb-2 text-center">Feature Engineering</span>
                <span className="text-xs font-mono text-neon-cyan text-center font-bold">eve_contrib =<br/>max(0, qber - 0.66*noise)</span>
              </div>
              <ArrowRight className="text-[#334155] shrink-0" size={24} />
              <div className="flex flex-col items-center justify-center p-5 bg-[#0B101A] border border-[#1A2639] rounded-lg min-w-[180px] transition-all">
                <Cpu className="text-white/70 mb-3" size={20} />
                <span className="text-[9px] text-[#64748B] font-sans uppercase tracking-[0.2em] mb-2 text-center">Model Mapping</span>
                <span className="text-xs font-mono text-white text-center">{selectedModel.name}<br/>Inference</span>
              </div>
              <ArrowRight className={`${isHighThreat ? 'text-neon-red drop-shadow-[0_0_8px_rgba(255,0,60,0.8)]' : 'text-neon-cyan drop-shadow-[0_0_8px_rgba(0,240,255,0.6)]'} shrink-0`} size={24} />
              <div className={`flex flex-col items-center justify-center p-5 rounded-lg min-w-[180px] relative overflow-hidden transition-all duration-500 border-2 ${isHighThreat ? 'bg-neon-red border-[#FF003C] shadow-[0_0_25px_rgba(255,0,60,0.4)]' : 'bg-[#0B101A] border-neon-cyan shadow-[0_0_15px_rgba(0,240,255,0.2)]'}`}>
                {isHighThreat ? <ShieldAlert className="text-white mb-2 relative z-10" size={28} /> : <ShieldCheck className="text-neon-cyan mb-2 relative z-10" size={28} />}
                <span className={`text-[9px] font-sans uppercase tracking-[0.2em] mb-1 relative z-10 ${isHighThreat ? 'text-white/80' : 'text-neon-cyan/80'}`}>THREAT LEVEL</span>
                <span className={`text-lg font-mono font-bold tracking-widest relative z-10 shadow-black drop-shadow-md ${isHighThreat ? 'text-white' : 'text-neon-cyan'}`}>{threatLevel}</span>
              </div>
            </div>
          </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
};

export default MLAnalysis;
