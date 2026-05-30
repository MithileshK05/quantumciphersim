import React, { useState } from 'react';
import { useQKDMetrics } from '../hooks/useQKDMetrics';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ArrowRight, Database, Cpu, Activity, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useSimulation } from '../context/SimulationContext';

const modelsConfig = [
  { id: 'gradient_boosting', name: 'Gradient Boosting', acc: 0.9376, prec: 0.9536, rec: 0.9574, f1: 0.9555 },
  { id: 'random_forest', name: 'Random Forest', acc: 0.9351, prec: 0.9580, rec: 0.9488, f1: 0.9534 },
  { id: 'logistic_regression', name: 'Logistic Regression', acc: 0.9306, prec: 0.9755, rec: 0.9240, f1: 0.9491 },
  { id: 'svm', name: 'Support Vector Machine', acc: 0.9278, prec: 0.9772, rec: 0.9183, f1: 0.9468 }
];

const MLAnalysis = () => {
  const [selectedModelId, setSelectedModelId] = useState('gradient_boosting');
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

  const selectedModel = modelsConfig.find(m => m.id === selectedModelId);

  // Derived threat data for BarChart
  // Three clear states:
  //  1. No attack        → Secure Channel dominant (cyan, large)
  //  2. Attack, no mitigation → Intercept-Resend dominant (bright red, large)
  //  3. Attack, mitigated → Attack bar in AMBER sized by eve_contribution (varies per model)
  const { threatData, threatLevel, isHighThreat, isMitigated } = React.useMemo(() => {
    const confidenceScore   = metrics?.confidence_score  ?? 0;
    const rawThreatLevel    = metrics?.threat_level      || 'LOW';
    const mitigationStatus  = metrics?.mitigation_status || 'NONE';
    const eveContribution   = metrics?.eve_contribution  ?? 0;
    const mitigated = mitigationStatus === 'PA_ACTIVE' || mitigationStatus === 'E91_ACTIVE';

    let attackValue, secureValue, attackFill, effectiveThreat;

    if (mitigated) {
      // Privacy Amplification (PA) mathematically eliminates Eve's key knowledge.
      // After PA: the remaining key bits are effectively secure (~93-95%).
      // Show a SMALL amber residual (~5-7%) = the detected+neutralized threat,
      // and a LARGE cyan bar (~93-95%) = post-PA channel security.
      // Scale: eve_contribution ~0.20-0.28 → amber bar ~5-7%
      attackValue    = Math.max(eveContribution * 25, 4);  // 5-7% amber residual
      secureValue    = 100 - attackValue;                   // 93-95% secure
      attackFill     = '#FF9500'; // amber = detected but neutralized
      effectiveThreat = 'LOW';

    } else {
      // Raw ML detection: show confidence difference clearly between models
      attackValue    = confidenceScore * 100;
      secureValue    = (1 - confidenceScore) * 100;
      attackFill     = '#FF003C'; // red = active threat
      effectiveThreat = rawThreatLevel;
    }

    const label = mitigated
      ? `MITIGATED (${mitigationStatus.replace('_', ' ')})`
      : effectiveThreat;

    return {
      threatData: [
        { name: 'Intercept-Resend Attack', value: attackValue,  fill: attackFill },
        { name: 'Secure Channel',          value: secureValue,  fill: '#00F0FF'  }
      ],
      threatLevel:  label,
      isHighThreat: effectiveThreat.toUpperCase() === 'HIGH',
      isMitigated:  mitigated
    };
  }, [metrics?.confidence_score, metrics?.threat_level, metrics?.mitigation_status, metrics?.eve_contribution]);



  return (
    <div className="h-full w-full bg-[#030508] text-text-main overflow-y-auto custom-scrollbar p-6">
      
      {/* Header Area */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-sans tracking-wide glow-cyan text-neon-cyan uppercase">Machine Learning Analysis</h1>
        <button 
          onClick={() => setIsAttacked(!isAttacked)}
          className={`px-6 py-2 rounded font-mono text-sm tracking-widest uppercase transition-all duration-300 font-bold border ${isAttacked ? 'bg-neon-red/20 text-neon-red border-neon-red glow-red' : 'bg-transparent text-[#64748B] border-[#1A2639] hover:border-neon-cyan hover:text-neon-cyan'}`}
        >
          {isAttacked ? "SIMULATING ATTACK: ON" : "SIMULATING ATTACK: OFF"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-12">
        
        {/* Left Column (Configuration) */}
        <div className="col-span-1 lg:col-span-4 flex flex-col gap-6">
          <div className="glass-panel p-6 rounded-xl border border-quantum-border flex flex-col gap-6 sticky top-6">
            <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans border-b border-[#1A2639] pb-4 font-bold">ML Model Configuration</h2>
            
            <div className="flex flex-col gap-3">
              <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest pl-1">Active Model</label>
              <select 
                value={selectedModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                className="w-full bg-[#0B101A] border border-[#1A2639] text-text-main p-3 rounded font-mono text-sm focus:outline-none focus:border-neon-cyan focus:ring-1 focus:ring-neon-cyan transition-colors"
              >
                {modelsConfig.map(model => (
                  <option key={model.id} value={model.id}>{model.name}</option>
                ))}
              </select>
            </div>

            {/* Premium Dataset Selection with Slider Style */}
            <div className="flex flex-col gap-3">
              <label className="text-[10px] uppercase font-sans text-neon-cyan tracking-widest pl-1">Training Dataset</label>
              <div className="space-y-4">
                <select 
                  disabled
                  className="w-full bg-[rgba(11,16,26,0.6)] border border-[#1A2639] text-[#64748B] p-3 rounded font-mono text-sm uppercase"
                >
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

          </div>
        </div>

        {/* Right Column (Analytics) */}
        <div className="col-span-1 lg:col-span-8 flex flex-col gap-8">
          
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
               {/* Feat 1: Raw QBER */}
               <div className={`glass-panel border rounded p-4 flex flex-col justify-between transition-colors duration-500 ${isHighThreat ? 'bg-red-900/20 border-neon-red shadow-[0_0_15px_rgba(255,0,60,0.2)] text-neon-red glow-red' : 'bg-[#0B101A] border-[#1A2639] text-white'}`}>
                  <span className="text-[10px] uppercase tracking-widest font-sans opacity-70 mb-2">RAW QBER</span>
                  <span className="text-2xl font-mono font-bold">{metrics ? (metrics.qber * 100).toFixed(2) : '0.00'}%</span>
               </div>

               {/* Feat 2: Channel Noise */}
               <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between transition-colors duration-500">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">CHANNEL NOISE</span>
                  <span className="text-2xl font-mono text-[#E2E8F0] font-bold">{metrics ? metrics.noise_level.toFixed(3) : '0.000'}</span>
               </div>

               {/* Feat 3: Sifted Key Length */}
               <div className="glass-panel bg-[#0B101A] border-[#1A2639] border rounded p-4 flex flex-col justify-between transition-colors duration-500">
                  <span className="text-[10px] uppercase tracking-widest font-sans text-[#64748B] mb-2">SIFTED KEY</span>
                  <span className="text-2xl font-mono text-neon-cyan font-bold">{metrics ? metrics.sifted_key_length : '0'}</span>
               </div>

               {/* Feat 4: Eve Contribution */}
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
              
              {/* Block 1 */}
              <div className="flex flex-col items-center justify-center p-5 bg-[#0B101A] border border-[#1A2639] rounded-lg min-w-[180px]">
                <Database className="text-[#64748B] mb-3" size={20} />
                <span className="text-[9px] text-[#64748B] font-sans uppercase tracking-[0.2em] mb-2 text-center">Observable Extraction</span>
                <span className="text-xs font-mono text-white text-center">QBER: {metrics?.qber.toFixed(3)}<br/>Noise: {metrics?.noise_level.toFixed(3)}</span>
              </div>

              <ArrowRight className="text-[#334155] shrink-0" size={24} />

              {/* Block 2 Mathematically Highlighted */}
              <div className="flex flex-col items-center justify-center p-5 bg-[#0A0E17] border border-neon-cyan/30 shadow-[0_0_10px_rgba(0,240,255,0.1)] rounded-lg min-w-[200px]">
                <Activity className="text-neon-cyan mb-3" size={20} />
                <span className="text-[9px] text-[#00F0FF] font-sans uppercase tracking-[0.2em] mb-2 text-center">Feature Engineering</span>
                <span className="text-xs font-mono text-neon-cyan text-center font-bold">eve_contrib =<br/>max(0, qber - 0.66*noise)</span>
              </div>

              <ArrowRight className="text-[#334155] shrink-0" size={24} />

              {/* Block 3 */}
              <div className="flex flex-col items-center justify-center p-5 bg-[#0B101A] border border-[#1A2639] rounded-lg min-w-[180px] transition-all">
                <Cpu className="text-white/70 mb-3" size={20} />
                <span className="text-[9px] text-[#64748B] font-sans uppercase tracking-[0.2em] mb-2 text-center">Model Mapping</span>
                <span className="text-xs font-mono text-white text-center">{selectedModel.name}<br/>Inference</span>
              </div>

              <ArrowRight className={`${isHighThreat ? 'text-neon-red drop-shadow-[0_0_8px_rgba(255,0,60,0.8)]' : 'text-neon-cyan drop-shadow-[0_0_8px_rgba(0,240,255,0.6)]'} shrink-0`} size={24} />

              {/* Block 4 */}
              <div className={`flex flex-col items-center justify-center p-5 rounded-lg min-w-[180px] relative overflow-hidden transition-all duration-500 border-2 ${isHighThreat ? 'bg-neon-red border-[#FF003C] shadow-[0_0_25px_rgba(255,0,60,0.4)]' : 'bg-[#0B101A] border-neon-cyan shadow-[0_0_15px_rgba(0,240,255,0.2)]'}`}>
                {isHighThreat ? <ShieldAlert className="text-white mb-2 relative z-10" size={28} /> : <ShieldCheck className="text-neon-cyan mb-2 relative z-10" size={28} />}
                <span className={`text-[9px] font-sans uppercase tracking-[0.2em] mb-1 relative z-10 ${isHighThreat ? 'text-white/80' : 'text-neon-cyan/80'}`}>THREAT LEVEL</span>
                <span className={`text-lg font-mono font-bold tracking-widest relative z-10 shadow-black drop-shadow-md ${isHighThreat ? 'text-white' : 'text-neon-cyan'}`}>{threatLevel}</span>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default MLAnalysis;
