import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts';
import {
  Clock, ShieldAlert, ShieldCheck, Filter, RefreshCw,
  Database, Activity, TrendingUp, AlertTriangle, Cpu
} from 'lucide-react';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Ensure timestamps are treated as UTC so browser correctly converts to local timezone (IST)
const parseUtcDate = (ts) => {
  if (!ts) return new Date();
  const isoStr = ts.includes('T') ? ts : ts.replace(' ', 'T');
  return new Date(isoStr.endsWith('Z') ? isoStr : isoStr + 'Z');
};

// ── Data fetching ─────────────────────────────────────────────────────────────
const fetchHistory = async (limit) => {
  const res = await axios.get(`${BASE_URL}/history`, { params: { limit } });
  return res.data;
};

// ── Sub-components ────────────────────────────────────────────────────────────

const StatCard = ({ icon: Icon, label, value, sub, accent = false, danger = false }) => (
  <div className={`glass-panel rounded-xl border p-5 flex flex-col gap-2 relative overflow-hidden
    ${danger  ? 'border-neon-red/40 bg-red-950/20 shadow-[0_0_20px_rgba(255,0,60,0.08)]'
    : accent  ? 'border-neon-cyan/30 bg-[#0B101A] shadow-[0_0_20px_rgba(0,240,255,0.08)]'
    :           'border-quantum-border bg-[#0B101A]'}`}
  >
    <div className="absolute top-0 left-0 w-1 h-full bg-neon-cyan opacity-60 shadow-[0_0_8px_#00F0FF]" />
    <div className="flex items-center gap-2 pl-2">
      <Icon size={14} className={danger ? 'text-neon-red' : 'text-neon-cyan'} />
      <span className="text-[10px] uppercase tracking-[0.2em] font-sans text-[#64748B] font-bold">{label}</span>
    </div>
    <span className={`text-3xl font-mono font-bold pl-2 ${danger ? 'text-neon-red' : accent ? 'text-neon-cyan drop-shadow-[0_0_6px_#00F0FF]' : 'text-white'}`}>
      {value}
    </span>
    {sub && <span className="text-[11px] font-mono text-[#64748B] pl-2">{sub}</span>}
  </div>
);

const ThreatBadge = ({ level }) => {
  if (!level) return <span className="text-[#334155] font-mono text-xs">—</span>;
  const isHigh = level.toUpperCase() === 'HIGH';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-widest uppercase
      ${isHigh ? 'bg-neon-red/20 text-neon-red border border-neon-red/40' : 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30'}`}>
      {isHigh ? <ShieldAlert size={10} /> : <ShieldCheck size={10} />}
      {level}
    </span>
  );
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-[#030508] border border-[#1A2639] rounded p-3 font-mono text-xs text-[#E2E8F0] shadow-xl">
      <p className="text-neon-cyan mb-1">{label}</p>
      <p>QBER: <span className="text-white font-bold">{(d?.final_qber * 100)?.toFixed(2)}%</span></p>
      {d?.ml_prediction && <p>Prediction: <ThreatBadge level={d.ml_prediction} /></p>}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
const History = () => {
  const [limit, setLimit]           = useState(50);
  const [filterProtocol, setFilter] = useState('ALL'); // ALL | HIGH | LOW
  const [showLimit, setShowLimit]   = useState(20);    // rows shown in table

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['history', limit],
    queryFn:  () => fetchHistory(limit),
    staleTime: 10_000,       // Re-fetch every 10 s
    refetchInterval: 15_000,
  });

  const runs = data?.runs ?? [];

  // ── Derived stats ───────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!runs.length) return null;
    const withQber    = runs.filter(r => r.final_qber != null);
    const avgQber     = withQber.length
      ? withQber.reduce((s, r) => s + r.final_qber, 0) / withQber.length
      : 0;
    const attacks     = runs.filter(r => r.actual_attack_status === true).length;
    const highPred    = runs.filter(r => r.ml_prediction === 'HIGH').length;
    const maxQber     = withQber.length ? Math.max(...withQber.map(r => r.final_qber)) : 0;
    return { total: runs.length, avgQber, attacks, highPred, maxQber };
  }, [runs]);

  // ── Filtered rows ───────────────────────────────────────────────────────────
  const filteredRuns = useMemo(() => {
    if (filterProtocol === 'ALL')  return runs;
    if (filterProtocol === 'HIGH') return runs.filter(r => r.ml_prediction === 'HIGH');
    if (filterProtocol === 'LOW')  return runs.filter(r => r.ml_prediction === 'LOW');
    if (filterProtocol === 'ATTACK') return runs.filter(r => r.actual_attack_status === true);
    return runs;
  }, [runs, filterProtocol]);

  // ── QBER chart data (chronological order) ──────────────────────────────────
  const chartData = useMemo(() =>
    [...runs]
      .filter(r => r.final_qber != null && r.timestamp)
      .sort((a, b) => parseUtcDate(a.timestamp) - parseUtcDate(b.timestamp))
      .map(r => ({
        ...r,
        time: parseUtcDate(r.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        qberPct: +(r.final_qber * 100).toFixed(3),
      })),
  [runs]);

  const visibleRows = filteredRuns.slice(0, showLimit);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="h-full w-full bg-[#030508] text-text-main overflow-y-auto custom-scrollbar p-6">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-sans tracking-wide glow-cyan text-neon-cyan uppercase">
            Session History
          </h1>
          <p className="text-[#64748B] text-xs font-mono mt-1 tracking-wide">
            {data ? `${data.total} total simulation runs in PostgreSQL database` : 'Loading database…'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Limit selector */}
          <select
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            className="bg-[#0B101A] border border-[#1A2639] text-[#94A3B8] p-2 rounded font-mono text-xs focus:outline-none focus:border-neon-cyan transition-colors"
          >
            <option value={20}>Last 20</option>
            <option value={50}>Last 50</option>
            <option value={100}>Last 100</option>
            <option value={200}>Last 200</option>
          </select>
          {/* Refresh */}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-2 px-4 py-2 rounded font-mono text-xs tracking-widest uppercase border border-[#1A2639] text-[#64748B] hover:border-neon-cyan hover:text-neon-cyan transition-all duration-200 disabled:opacity-50"
          >
            <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Loading / Error states ──────────────────────────────────────────── */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <div className="w-8 h-8 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin" />
          <span className="text-[#64748B] font-mono text-sm tracking-widest">LOADING HISTORY…</span>
        </div>
      )}

      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center h-64 gap-4 border border-neon-red/30 rounded-xl bg-red-950/10 p-8">
          <AlertTriangle className="text-neon-red" size={36} />
          <p className="text-neon-red font-mono text-sm tracking-wide">Failed to load history from backend.</p>
          <p className="text-[#64748B] font-mono text-xs">Make sure the Render backend is awake and the database is connected.</p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-5 py-2 rounded border border-neon-red/40 text-neon-red font-mono text-xs tracking-widest hover:bg-neon-red/10 transition-all"
          >
            RETRY
          </button>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* ── Stat Cards ───────────────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={Database}      label="Total Runs"     value={stats?.total ?? 0}                         accent />
            <StatCard icon={Activity}      label="Avg QBER"       value={`${((stats?.avgQber ?? 0) * 100).toFixed(2)}%`}   sub="Quantum Bit Error Rate" />
            <StatCard icon={ShieldAlert}   label="Attacks Logged" value={stats?.attacks ?? 0}                        danger={stats?.attacks > 0} sub="actual_attack_status=true" />
            <StatCard icon={TrendingUp}    label="High Threat"    value={stats?.highPred ?? 0}                        sub="ML predicted HIGH" danger={stats?.highPred > 0} />
          </div>

          {/* ── QBER Trend Chart ─────────────────────────────────────────────── */}
          {chartData.length > 1 && (
            <div className="glass-panel p-6 rounded-xl border border-quantum-border mb-8">
              <div className="flex items-center gap-3 border-b border-[#1A2639] pb-4 mb-6">
                <Activity className="text-neon-cyan" size={14} />
                <h2 className="text-[#64748B] text-xs uppercase tracking-[0.2em] font-sans font-bold">
                  QBER Over Time (%)
                </h2>
                <span className="ml-auto text-[10px] font-mono text-neon-cyan bg-neon-cyan/10 px-2 py-1 rounded tracking-widest">
                  {chartData.length} data points
                </span>
              </div>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid stroke="#1A2639" strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      stroke="#1A2639"
                      tick={{ fill: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 10 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      stroke="#1A2639"
                      tick={{ fill: '#64748B', fontFamily: 'JetBrains Mono', fontSize: 10 }}
                      tickFormatter={v => `${v}%`}
                      domain={[0, 'auto']}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    {/* 11% QBER threshold = eavesdropping likely */}
                    <ReferenceLine y={11} stroke="#FF003C" strokeDasharray="4 4"
                      label={{ value: 'QBER 11% threshold', fill: '#FF003C', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="qberPct"
                      stroke="#00F0FF"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: '#00F0FF', stroke: '#030508', strokeWidth: 2 }}
                      style={{ filter: 'drop-shadow(0 0 6px rgba(0,240,255,0.5))' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* ── Filter bar ───────────────────────────────────────────────────── */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <Filter size={12} className="text-[#64748B]" />
            <span className="text-[10px] uppercase tracking-widest text-[#64748B] font-sans">Filter:</span>
            {['ALL', 'HIGH', 'LOW', 'ATTACK'].map(f => (
              <button
                key={f}
                onClick={() => { setFilter(f); setShowLimit(20); }}
                className={`px-3 py-1 rounded text-[10px] font-mono tracking-widest uppercase border transition-all duration-200
                  ${filterProtocol === f
                    ? 'bg-neon-cyan/20 border-neon-cyan text-neon-cyan shadow-[0_0_8px_rgba(0,240,255,0.3)]'
                    : 'border-[#1A2639] text-[#64748B] hover:border-neon-cyan/50 hover:text-[#94A3B8]'
                  }`}
              >
                {f === 'ATTACK' ? '⚠ Real Attack' : f}
                {f !== 'ALL' && (
                  <span className="ml-1 opacity-60">
                    ({f === 'HIGH'   ? runs.filter(r => r.ml_prediction === 'HIGH').length
                    : f === 'LOW'    ? runs.filter(r => r.ml_prediction === 'LOW').length
                    : runs.filter(r => r.actual_attack_status === true).length})
                  </span>
                )}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-[#334155] font-mono">
              Showing {Math.min(showLimit, filteredRuns.length)} of {filteredRuns.length}
            </span>
          </div>

          {/* ── Table ────────────────────────────────────────────────────────── */}
          {filteredRuns.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 border border-[#1A2639] rounded-xl gap-3">
              <Clock className="text-[#334155]" size={32} />
              <p className="text-[#64748B] font-mono text-sm">No simulation runs recorded yet.</p>
              <p className="text-[#334155] font-mono text-xs">Run a simulation on the Sim page to populate history.</p>
            </div>
          ) : (
            <div className="glass-panel rounded-xl border border-quantum-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#1A2639] bg-[#0B101A]">
                      {['Timestamp', 'QBER', 'Noise', 'Attack Prob.', 'Sifted Key', 'Eve Contrib.', 'ML Prediction', 'Confidence', 'Model Used', 'Ground Truth'].map(h => (
                        <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-[0.15em] text-[#64748B] font-sans whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row, i) => {
                      const isHighRow = row.ml_prediction === 'HIGH';
                      const isAttack  = row.actual_attack_status === true;
                      return (
                        <tr
                          key={row.session_id}
                          className={`border-b border-[#0F1520] transition-colors duration-150 hover:bg-[#0B101A]
                            ${isHighRow && isAttack ? 'bg-red-950/10' : ''}`}
                        >
                          {/* Timestamp */}
                          <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                            {row.timestamp
                              ? parseUtcDate(row.timestamp).toLocaleString('en-US', {
                                  month: 'short', day: 'numeric',
                                  hour: '2-digit', minute: '2-digit', second: '2-digit'
                                })
                              : '—'}
                          </td>
                          {/* QBER */}
                          <td className={`px-4 py-3 font-bold whitespace-nowrap
                            ${(row.final_qber ?? 0) > 0.11 ? 'text-neon-red' : 'text-neon-cyan'}`}>
                            {row.final_qber != null ? `${(row.final_qber * 100).toFixed(2)}%` : '—'}
                          </td>
                          {/* Noise */}
                          <td className="px-4 py-3 text-[#94A3B8]">
                            {row.noise_level != null ? row.noise_level.toFixed(3) : '—'}
                          </td>
                          {/* Attack Prob */}
                          <td className="px-4 py-3 text-[#94A3B8]">
                            {row.attack_probability != null ? `${(row.attack_probability * 100).toFixed(0)}%` : '—'}
                          </td>
                          {/* Sifted Key */}
                          <td className="px-4 py-3 text-[#94A3B8]">
                            {row.sifted_key_length ?? '—'}
                          </td>
                          {/* Eve Contrib */}
                          <td className={`px-4 py-3 font-bold
                            ${(row.eve_qber_contribution ?? 0) > 0.01 ? 'text-amber-400' : 'text-[#64748B]'}`}>
                            {row.eve_qber_contribution != null ? row.eve_qber_contribution.toFixed(4) : '—'}
                          </td>
                          {/* ML Prediction */}
                          <td className="px-4 py-3">
                            <ThreatBadge level={row.ml_prediction} />
                          </td>
                          {/* Confidence */}
                          <td className="px-4 py-3 text-[#94A3B8]">
                            {row.confidence_score != null ? `${(row.confidence_score * 100).toFixed(1)}%` : '—'}
                          </td>
                          {/* Model Used */}
                          <td className="px-4 py-3 text-[#64748B] whitespace-nowrap">
                            {row.model_used
                              ? row.model_used.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                              : '—'}
                          </td>
                          {/* Ground Truth */}
                          <td className="px-4 py-3">
                            {row.actual_attack_status === true  && <span className="text-neon-red font-bold">ATTACKED</span>}
                            {row.actual_attack_status === false && <span className="text-neon-cyan">SECURE</span>}
                            {row.actual_attack_status == null  && <span className="text-[#334155]">—</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Load more */}
              {filteredRuns.length > showLimit && (
                <div className="border-t border-[#1A2639] p-4 flex justify-center">
                  <button
                    onClick={() => setShowLimit(s => s + 20)}
                    className="px-6 py-2 rounded border border-[#1A2639] text-[#64748B] font-mono text-xs tracking-widest uppercase hover:border-neon-cyan hover:text-neon-cyan transition-all duration-200"
                  >
                    Load 20 more ({filteredRuns.length - showLimit} remaining)
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Footer note ──────────────────────────────────────────────────── */}
          <p className="mt-6 text-center text-[10px] text-[#1A2639] font-mono tracking-widest">
            Data stored in PostgreSQL on Render · Auto-refreshes every 15s · Session IDs are UUIDs
          </p>
        </>
      )}
    </div>
  );
};

export default History;
