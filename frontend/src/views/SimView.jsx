import { useState, useEffect, useMemo } from 'react';
import { useQKDMetrics } from '../hooks/useQKDMetrics';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { QuantumChannel } from '../components/3d/QuantumChannel';
import { useSimulation } from '../context/SimulationContext';

const SimView = () => {
  // ── State Setup ──────────────────────────────────────────────────────────
  const { 
    isAttacked, setIsAttacked,
    noiseLevel, setNoiseLevel,
    autoMitigate, setAutoMitigate,
    activeProtocol, setActiveProtocol
  } = useSimulation();

  // Rolling state buffer for streaming data (max 40 points)
  const [dataStream, setDataStream] = useState([]);

  // Hook with structuralSharing:false — always triggers re-render on every poll
  const { data: metrics, isLoading } = useQKDMetrics(
    noiseLevel,
    isAttacked ? 1.0 : 0.0,
    'gradient_boosting',
    autoMitigate,
    activeProtocol
  );

  // ── Data Stream — NO early-return guard (was the graph-freeze bug) ────────
  // Previously a lastUpdateRef check killed updates when backend returned
  // the same rounded values. Removed entirely — thermal noise in backend
  // guarantees values always differ slightly, and structuralSharing:false
  // guarantees re-renders. Double-fixed.
  useEffect(() => {
    if (!metrics) return;

    setDataStream(prev => {
      const timeStr = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: 'numeric',
        minute: 'numeric',
        second: 'numeric'
      });

      // Scale: QBER × 100 → percentage; Key Rate × 10 → kb/s display unit
      const newPoint = {
        time: timeStr,
        qber: parseFloat((metrics.qber * 100).toFixed(2)),
        key_rate: parseFloat((metrics.key_rate * 10).toFixed(2)),
      };

      const newArray = [...prev, newPoint];
      return newArray.length > 60 ? newArray.slice(newArray.length - 60) : newArray;
    });
  }, [metrics]);

  // ── Derived Display Values ─────────────────────────────────────────────
  const currentQBER = metrics ? (metrics.qber * 100).toFixed(2) : '0.00';
  const currentKeyRate = metrics ? (metrics.key_rate * 10).toFixed(2) : '0.00';
  const currentStatus = metrics ? metrics.status : 'CALIBRATING...';

  // ── PATCH v2 FIX: isCompromised must be false when mitigation is active ──
  // Previously, isCompromised stayed true from a stale ML prediction even after
  // PA or E91 shielding activated — poisoning the 3D channel color logic.
  const { isCompromised, isMitigating } = useMemo(() => {
    const mitStatus = metrics?.mitigation_status;
    const status = metrics?.status ?? '';
    const threat = metrics?.threat_level?.toUpperCase() ?? 'LOW';
    const isMitigated = mitStatus === 'PA_ACTIVE' || mitStatus === 'E91_ACTIVE';

    return {
      // Only mark as compromised if mitigation is NOT active
      isCompromised: !isMitigated && (
        status.includes('COMPROMISED') ||
        (threat === 'HIGH' && mitStatus === 'NONE')
      ),
      isMitigating: isMitigated,
    };
  }, [metrics?.status, metrics?.threat_level, metrics?.mitigation_status]);

  return (
    <div className="flex flex-row h-full w-full bg-transparent gap-6 p-4 animate-in fade-in duration-500">

      {/* 1. Left Column: Simulation Controls & Defense Measures */}
      <div className="w-1/4 flex flex-col gap-6">
        <div className="glass-panel rounded-xl border-quantum-border p-6 flex flex-col h-full relative overflow-hidden">
          {/* Top right corner decorative accent */}
          <div className="absolute top-0 right-0 w-24 h-24 bg-neon-cyan/5 rounded-bl-[100px]" />

          <h2 className="text-xl font-sans text-text-main font-bold tracking-widest mb-8 uppercase drop-shadow-md">Simulation</h2>

          {/* Noise Slider Control — using .quantum-slider class for premium styling */}
          <div className="flex flex-col gap-4 mb-8">
            <label className="text-[10px] font-sans text-text-muted uppercase tracking-widest flex justify-between">
              <span>Environmental Noise</span>
              <span className="text-neon-cyan font-mono font-bold glow-cyan">{noiseLevel.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0.01"
              max="0.15"
              step="0.01"
              value={noiseLevel}
              onChange={(e) => setNoiseLevel(parseFloat(e.target.value))}
              className="quantum-slider"
            />
          </div>

          {/* Eve Attack Toggle */}
          <div className="mb-10">
            <button
              onClick={() => setIsAttacked(!isAttacked)}
              className={`w-full py-3 rounded-lg font-mono text-xs tracking-widest uppercase transition-all duration-300 font-bold ${
                isAttacked
                ? "bg-neon-red text-quantum-void glow-red shadow-[0_0_20px_rgba(255,0,60,0.4)]"
                : "bg-[#0A0E17] text-neon-red border-[1px] border-neon-red/50 hover:bg-neon-red/5"
              }`}
            >
              {isAttacked ? 'ABORT ATTACK' : 'INJECT EVE'}
            </button>
          </div>

          {/* DEFENSE MEASURES SECTION */}
          <div className="mt-auto border-t border-quantum-border pt-8 flex flex-col gap-6">
            <h3 className="text-xs font-sans text-text-muted font-bold tracking-[0.2em] uppercase">Defense Measures</h3>

            {/* Auto-Mitigate Toggle */}
            <div className="flex items-center justify-between">
              <span className={`text-[10px] uppercase font-mono tracking-widest ${autoMitigate ? 'text-neon-cyan' : 'text-text-muted'}`}>
                Auto-Mitigation
              </span>
              <button
                onClick={() => setAutoMitigate(!autoMitigate)}
                className={`w-12 h-6 rounded-full relative transition-all duration-300 ${autoMitigate ? 'bg-neon-cyan' : 'bg-quantum-surface'}`}
              >
                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all duration-300 ${autoMitigate ? 'left-7' : 'left-1'}`} />
              </button>
            </div>

            {/* Hardware Routing Buttons */}
            <div className="flex flex-col gap-2">
              <label className="text-[9px] uppercase text-text-muted tracking-widest mb-1">Hardware Routing</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setActiveProtocol('BB84')}
                  className={`py-2 text-[10px] font-mono rounded border transition-all ${activeProtocol === 'BB84' ? 'border-neon-cyan text-neon-cyan bg-neon-cyan/5' : 'border-quantum-border text-text-muted'}`}
                >
                  BB84
                </button>
                <button
                  onClick={() => setActiveProtocol('E91')}
                  className={`py-2 text-[10px] font-mono rounded border transition-all ${activeProtocol === 'E91' ? 'border-neon-purple text-neon-purple bg-neon-purple/5 glow-purple' : 'border-quantum-border text-text-muted'}`}
                >
                  E91
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Right Column (Metrics & Telemetry) */}
      <div className="w-3/4 flex flex-col gap-6 h-full overflow-y-auto pb-8 pr-2 custom-scrollbar">

        {/* Hero Metrics */}
        <div className="grid grid-cols-3 gap-6 w-full shrink-0">
          <div className={`glass-panel p-6 rounded-xl border-quantum-border flex flex-col items-center justify-center transition-all duration-500 ${isCompromised ? 'glow-red' : isMitigating ? 'glow-purple border-neon-purple/50' : ''}`}>
            <span className="text-text-muted text-xs font-bold uppercase tracking-widest mb-3 font-sans">QUANTUM BIT ERROR RATE</span>
            <span className={`text-5xl font-mono font-bold transition-colors duration-500 ${isCompromised ? 'text-neon-red' : isMitigating ? 'text-neon-purple' : 'text-text-main'}`}>
              {currentQBER}%
            </span>
          </div>

          <div className="glass-panel p-6 rounded-xl border-quantum-border flex flex-col items-center justify-center">
            <span className="text-text-muted text-xs font-bold uppercase tracking-widest mb-3 font-sans">SECURE KEY RATE</span>
            <span className={`text-5xl font-mono font-bold transition-colors ${isMitigating && metrics?.active_protocol === 'BB84' ? 'text-neon-purple pulse-slow' : 'text-neon-cyan'}`}>
              {currentKeyRate} <span className="text-xl">kb/s</span>
            </span>
          </div>

          <div className={`glass-panel p-6 rounded-xl border-quantum-border flex flex-col items-center justify-center transition-all duration-500 ${isCompromised ? 'glow-red' : isMitigating ? 'glow-purple shadow-[0_0_20px_#B026FF22]' : ''}`}>
            <span className="text-text-muted text-xs font-bold uppercase tracking-widest mb-3 font-sans">NETWORK STATUS</span>
            <span className={`text-3xl font-mono font-bold uppercase tracking-widest text-center transition-colors duration-500 ${isCompromised ? 'text-neon-red animate-pulse' : isMitigating ? 'text-neon-purple animate-pulse' : 'text-neon-cyan glow-cyan'}`}>
              {currentStatus}
            </span>
          </div>
        </div>

        {/* Telemetry Chart */}
        <div className="glass-panel rounded-xl border-quantum-border w-full shrink-0 flex flex-col p-6 relative" style={{ height: '360px' }}>
          <h3 className="text-neon-cyan text-sm uppercase tracking-widest font-sans mb-4 glow-cyan w-max">LIVE TELEMETRY STREAM</h3>
          <div style={{ width: '100%', height: '280px' }}>
            {isLoading && dataStream.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <p className="text-neon-cyan animate-pulse font-mono tracking-widest glow-cyan text-lg">CALIBRATING QUANTUM CHANNEL...</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={dataStream} margin={{ top: 10, right: 30, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false} stroke="#1A2639" strokeDasharray="3 3" />
                  <XAxis dataKey="time" tick={false} axisLine={{ stroke: '#1A2639' }} />
                  {/* PATCH v2: auto-scale Y axis so values are readable at all states */}
                  <YAxis
                    type="number"
                    domain={['auto', 'auto']}
                    stroke="#1A2639"
                    tick={{ fill: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 11 }}
                    width={40}
                  />
                  <Tooltip
                    cursor={{ stroke: '#00F0FF', strokeWidth: 1 }}
                    contentStyle={{ backgroundColor: '#0B101A', borderColor: '#00F0FF44', borderRadius: '8px', fontFamily: 'JetBrains Mono', fontSize: '11px' }}
                    formatter={(value, name) => [
                      name === 'QBER (%)' ? `${value}%` : `${value} kb/s`,
                      name
                    ]}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    wrapperStyle={{ fontSize: '10px', fontFamily: 'JetBrains Mono', paddingBottom: '8px' }}
                    formatter={(value) => <span style={{ color: value === 'QBER (%)' ? '#B026FF' : '#00F0FF' }}>{value}</span>}
                  />
                  <Line name="QBER (%)" type="basis" dataKey="qber" stroke="#B026FF" strokeWidth={2.5} dot={false} isAnimationActive={false} strokeLinecap="round" strokeLinejoin="round" />
                  <Line name="Key Rate (×10 kb/s)" type="basis" dataKey="key_rate" stroke="#00F0FF" strokeWidth={3} dot={false} isAnimationActive={false} strokeLinecap="round" strokeLinejoin="round" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* 3D Physical Visualizer */}
        <div className="glass-panel rounded-xl border-quantum-border w-full shrink-0 flex flex-col p-6 gap-4 relative overflow-hidden" style={{ height: '440px' }}>
          <h3 className="text-text-muted text-xs uppercase tracking-[0.2em] font-sans">QUANTUM CHANNEL LINK</h3>
          <div style={{ width: '100%', height: '380px' }}>
            <QuantumChannel
              noiseLevel={noiseLevel}
              isCompromised={isCompromised}
              isAttacked={isAttacked}
              mitigationStatus={metrics?.mitigation_status ?? 'NONE'}
              activeProtocol={activeProtocol}
            />
          </div>
        </div>

      </div>
    </div>
  );
};

export default SimView;
