import React, { useState, useEffect } from 'react';
import { MotionItem, AccuracyComparisonResult } from '../../types';
import {
  Activity,
  Play,
  ChevronDown,
  Info,
  AlertCircle,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Beaker,
} from 'lucide-react';
import { fetchAccuracyMethods, compareAccuracy, fetchAccuracyBenchmarks } from '../../services/api';
import { MetricCard } from '../ui/MetricCard';
import { StatusBadge } from '../ui/StatusBadge';

interface AccuracyLabViewProps {
  motions: MotionItem[];
  selectedMotionId: string;
  onSelectMotion: (motionId: string) => void;
  onSetBVH: (primary: string, secondary?: string) => void;
  onViewModeChange?: (mode: 'side-by-side' | 'overlay') => void;
}

type TaskType = 'denoising' | 'gap_filling' | 'retargeting';

const TASK_CONFIGS = {
  denoising: {
    label: 'Task 1: Denoising',
    color: 'text-cyan-400',
    accent: 'border-cyan-800 bg-cyan-950/20',
    badge: '30%',
    configKey: 'noise_level',
    configOptions: ['LOW', 'MEDIUM', 'HIGH'],
    configLabel: 'Noise Level',
    defaultBaseline: 'baseline_savgol',
    defaultExperimental: 'butterworth',
  },
  gap_filling: {
    label: 'Task 2: Gap Filling',
    color: 'text-emerald-400',
    accent: 'border-emerald-800 bg-emerald-950/20',
    badge: '30%',
    configKey: 'gap_type',
    configOptions: ['SHORT', 'MEDIUM', 'LONG'],
    configLabel: 'Gap Difficulty',
    defaultBaseline: 'natural_cubic',
    defaultExperimental: 'pchip',
  },
  retargeting: {
    label: 'Task 3: Retargeting',
    color: 'text-purple-400',
    accent: 'border-purple-800 bg-purple-950/20',
    badge: '40%',
    configKey: 'target_type',
    configOptions: ['target_small', 'target_medium', 'target_tall'],
    configLabel: 'Target Avatar',
    defaultBaseline: 'baseline',
    defaultExperimental: 'contact_aware',
  },
};

function ErrorCurveChart({
  data,
  gapInterval,
}: {
  data: Array<{ frame: number; baseline_error: number; experimental_error: number }>;
  gapInterval?: [number, number] | null;
}) {
  if (!data || data.length === 0) return null;

  const W = 420;
  const H = 80;
  const pad = { l: 32, r: 8, t: 6, b: 18 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const maxErr = Math.max(...data.map((d) => Math.max(d.baseline_error, d.experimental_error)), 0.001);
  const minFrame = data[0].frame;
  const maxFrame = data[data.length - 1].frame;
  const frameRange = Math.max(1, maxFrame - minFrame);

  const toX = (f: number) => pad.l + ((f - minFrame) / frameRange) * plotW;
  const toY = (v: number) => pad.t + plotH - (v / maxErr) * plotH;

  const bLine = data.map((d, i) => `${i === 0 ? 'M' : 'L'}${toX(d.frame).toFixed(1)},${toY(d.baseline_error).toFixed(1)}`).join(' ');
  const eLine = data.map((d, i) => `${i === 0 ? 'M' : 'L'}${toX(d.frame).toFixed(1)},${toY(d.experimental_error).toFixed(1)}`).join(' ');

  return (
    <div className="w-full overflow-x-auto">
      <svg width={W} height={H} className="block">
        {/* Gap interval highlight */}
        {gapInterval && (
          <rect
            x={toX(gapInterval[0])}
            y={pad.t}
            width={toX(gapInterval[1]) - toX(gapInterval[0])}
            height={plotH}
            fill="#f59e0b22"
          />
        )}
        {/* Zero line */}
        <line x1={pad.l} y1={pad.t + plotH} x2={pad.l + plotW} y2={pad.t + plotH} stroke="#334155" strokeWidth={1} />
        {/* Y axis ticks */}
        <text x={pad.l - 2} y={pad.t + 4} textAnchor="end" fontSize={8} fill="#64748b">{maxErr.toFixed(2)}</text>
        <text x={pad.l - 2} y={pad.t + plotH} textAnchor="end" fontSize={8} fill="#64748b">0</text>
        {/* Baseline curve */}
        <path d={bLine} fill="none" stroke="#f59e0b" strokeWidth={1.5} opacity={0.85} />
        {/* Experimental curve */}
        <path d={eLine} fill="none" stroke="#06b6d4" strokeWidth={1.5} opacity={0.85} />
        {/* Frame axis label */}
        <text x={pad.l} y={H - 2} fontSize={8} fill="#475569">Frame {minFrame}</text>
        <text x={pad.l + plotW} y={H - 2} textAnchor="end" fontSize={8} fill="#475569">Frame {maxFrame}</text>
      </svg>
      <div className="flex items-center gap-4 mt-1">
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-amber-400 rounded" />
          <span className="text-[10px] text-theme-muted">Baseline</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-cyan-400 rounded" />
          <span className="text-[10px] text-theme-muted">Experimental</span>
        </div>
      </div>
    </div>
  );
}

export const AccuracyLabView: React.FC<AccuracyLabViewProps> = ({
  motions,
  selectedMotionId,
  onSelectMotion,
  onSetBVH,
  onViewModeChange,
}) => {
  const [activeTask, setActiveTask] = useState<TaskType>('denoising');
  const [configValue, setConfigValue] = useState<string>('MEDIUM');
  const [methodBaseline, setMethodBaseline] = useState<string>(TASK_CONFIGS.denoising.defaultBaseline);
  const [methodExperimental, setMethodExperimental] = useState<string>(TASK_CONFIGS.denoising.defaultExperimental);
  const [methods, setMethods] = useState<Record<string, Array<{ id: string; name: string; category: string; description: string }>>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<AccuracyComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [benchmarks, setBenchmarks] = useState<any | null>(null);
  const [activeView, setActiveView] = useState<'compare' | 'benchmarks'>('compare');

  useEffect(() => {
    fetchAccuracyMethods()
      .then(setMethods)
      .catch(() => {});
    fetchAccuracyBenchmarks()
      .then(setBenchmarks)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const cfg = TASK_CONFIGS[activeTask];
    setMethodBaseline(cfg.defaultBaseline);
    setMethodExperimental(cfg.defaultExperimental);
    const firstOption = cfg.configOptions[activeTask === 'denoising' ? 1 : 1];
    setConfigValue(firstOption || cfg.configOptions[0]);
    setResult(null);
    setError(null);
  }, [activeTask]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const cfg = TASK_CONFIGS[activeTask];
      const payload: {
        task: string;
        motion_id: string;
        method_baseline: string;
        method_experimental: string;
        noise_level?: string;
        gap_type?: string;
        target_type?: string;
      } = {
        task: activeTask,
        motion_id: selectedMotionId,
        method_baseline: methodBaseline,
        method_experimental: methodExperimental,
      };
      // Assign the task-specific config value using the correct key
      if (cfg.configKey === 'noise_level') payload.noise_level = configValue;
      else if (cfg.configKey === 'gap_type') payload.gap_type = configValue;
      else if (cfg.configKey === 'target_type') payload.target_type = configValue;

      const res = await compareAccuracy(payload);
      setResult(res as AccuracyComparisonResult);

      // Push BVHs to viewer
      if (res.baseline_bvh && res.experimental_bvh) {
        onSetBVH(res.baseline_bvh, res.experimental_bvh);
        onViewModeChange?.('side-by-side');
      }
    } catch (err: any) {
      setError(err.message || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  const currentMethods = methods[activeTask] || [];
  const baselineMethods = currentMethods.filter((m) => m.category === 'baseline');
  const experimentalMethods = currentMethods.filter((m) => m.category === 'experimental');
  const cfg = TASK_CONFIGS[activeTask];

  const scoreDeltaPositive = result ? result.score_delta >= 0 : null;

  return (
    <div className="flex flex-col h-full overflow-y-auto" style={{ backgroundColor: 'var(--bg-page)' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b shrink-0"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-card-alt)' }}
      >
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-rose-400" />
          <span className="text-xs font-bold tracking-wide uppercase" style={{ color: 'var(--text-secondary)' }}>Accuracy Lab</span>
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded"
            style={{ color: 'var(--text-muted)', backgroundColor: 'var(--bg-inset)' }}
          >Phase 11</span>
        </div>
        <div className="flex items-center gap-1 text-[10px]">
          <button
            className={`px-2.5 py-1 rounded-md font-medium transition-colors ${activeView === 'compare' ? 'bg-rose-500/20 text-rose-300' : 'text-theme-muted hover:text-theme-secondary'}`}
            onClick={() => setActiveView('compare')}
          >Compare</button>
          <button
            className={`px-2.5 py-1 rounded-md font-medium transition-colors ${activeView === 'benchmarks' ? 'bg-slate-700 text-theme-secondary' : 'text-theme-muted hover:text-theme-secondary'}`}
            onClick={() => setActiveView('benchmarks')}
          >Benchmarks</button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {activeView === 'compare' ? (
          <>
            {/* Task Selector */}
            <div className="grid grid-cols-3 gap-1.5">
              {(Object.keys(TASK_CONFIGS) as TaskType[]).map((t) => {
                const tc = TASK_CONFIGS[t];
                const isActive = activeTask === t;
                return (
                  <button
                    key={t}
                    onClick={() => setActiveTask(t)}
                    className={`rounded-lg p-2 border text-left transition-all ${isActive ? tc.accent + ' border-opacity-100' : 'border-theme bg-slate-900/40 hover:bg-theme-hover/60'}`}
                  >
                    <div className={`text-[10px] font-bold uppercase tracking-wide ${isActive ? tc.color : 'text-theme-muted'}`}>
                      {tc.badge}
                    </div>
                    <div className="text-[10px] text-theme-secondary mt-0.5 leading-tight">{tc.label.replace('Task 1: ', '').replace('Task 2: ', '').replace('Task 3: ', '')}</div>
                  </button>
                );
              })}
            </div>

            {/* Configuration Panel */}
            <div className={`rounded-xl border p-3 flex flex-col gap-2.5 ${cfg.accent}`}>
              <h3 className="text-[11px] font-bold text-theme-secondary uppercase tracking-wide flex items-center gap-1.5">
                <Beaker className="w-3.5 h-3.5 text-rose-400" /> Experiment Configuration
              </h3>

              {/* Motion Selector */}
              <div>
                <label className="text-[10px] font-medium text-theme-muted block mb-1">Motion Sequence</label>
                <div className="relative">
                  <select
                    value={selectedMotionId}
                    onChange={(e) => onSelectMotion(e.target.value)}
                    className="w-full bg-theme-card border border-slate-700 text-theme-secondary text-[11px] rounded-lg px-2.5 py-1.5 appearance-none pr-7 focus:outline-none focus:border-rose-500/60"
                  >
                    {motions.map((m) => (
                      <option key={m.motion_id} value={m.motion_id}>
                        {m.motion_id} — {m.description.slice(0, 30)}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-3 h-3 text-theme-muted absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              {/* Config Level */}
              <div>
                <label className="text-[10px] font-medium text-theme-muted block mb-1">{cfg.configLabel}</label>
                <div className="flex gap-1.5">
                  {cfg.configOptions.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setConfigValue(opt)}
                      className={`flex-1 text-[10px] font-semibold py-1.5 rounded-lg border transition-colors ${configValue === opt ? 'border-rose-500 bg-rose-500/20 text-rose-300' : 'border-slate-700 bg-slate-900/50 text-theme-muted hover:border-slate-600'}`}
                    >
                      {opt.replace('target_', '')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Method Selectors */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-medium text-amber-400 block mb-1">Baseline Algorithm</label>
                  <div className="relative">
                    <select
                      value={methodBaseline}
                      onChange={(e) => setMethodBaseline(e.target.value)}
                      className="w-full bg-theme-card border border-amber-800/50 text-theme-secondary text-[10px] rounded-lg px-2 py-1.5 appearance-none pr-6 focus:outline-none"
                    >
                      {[...baselineMethods, ...experimentalMethods].map((m) => (
                        <option key={m.id} value={m.id}>{m.name.replace(' (Official Baseline)', '').replace(' (Improved)', '')}</option>
                      ))}
                    </select>
                    <ChevronDown className="w-3 h-3 text-theme-muted absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className="text-[10px] font-medium text-cyan-400 block mb-1">Experimental Algorithm</label>
                  <div className="relative">
                    <select
                      value={methodExperimental}
                      onChange={(e) => setMethodExperimental(e.target.value)}
                      className="w-full bg-theme-card border border-cyan-800/50 text-theme-secondary text-[10px] rounded-lg px-2 py-1.5 appearance-none pr-6 focus:outline-none"
                    >
                      {[...baselineMethods, ...experimentalMethods].map((m) => (
                        <option key={m.id} value={m.id}>{m.name.replace(' (Official Baseline)', '').replace(' (Improved)', '')}</option>
                      ))}
                    </select>
                    <ChevronDown className="w-3 h-3 text-theme-muted absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  </div>
                </div>
              </div>

              <button
                onClick={handleRun}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-rose-600/80 hover:bg-rose-600 text-theme-primary text-[11px] font-bold tracking-wide transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="w-3 h-3 rounded-full border border-white/30 border-t-white animate-spin" />
                    Running Comparison…
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" /> Run Comparative Evaluation
                  </>
                )}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl border border-red-800/60 bg-red-950/20 p-3 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-[11px] text-red-300 leading-relaxed">{error}</p>
              </div>
            )}

            {/* Results */}
            {result && (
              <>
                {/* Score Comparison */}
                <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between border-b border-theme pb-2">
                    <h3 className="text-[11px] font-bold text-theme-secondary uppercase tracking-wide">Score Comparison</h3>
                    <StatusBadge status="VALID" />
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    {/* Baseline */}
                    <div className="text-center rounded-lg bg-amber-950/30 border border-amber-800/40 p-2">
                      <div className="text-[9px] font-mono text-amber-400 uppercase tracking-wider mb-1">Baseline</div>
                      <div className="text-lg font-bold font-mono text-amber-300">{result.score_baseline.toFixed(1)}</div>
                      <div className="text-[9px] text-theme-muted">/ 100</div>
                    </div>
                    {/* Delta */}
                    <div className="text-center rounded-lg bg-slate-800/50 p-2 flex flex-col items-center justify-center">
                      {scoreDeltaPositive ? (
                        <ArrowUpRight className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <ArrowDownRight className="w-5 h-5 text-red-400" />
                      )}
                      <div className={`text-sm font-bold font-mono ${scoreDeltaPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                        {result.score_delta > 0 ? '+' : ''}{result.score_delta.toFixed(1)}
                      </div>
                      <div className="text-[9px] text-theme-muted">pts delta</div>
                    </div>
                    {/* Experimental */}
                    <div className="text-center rounded-lg bg-cyan-950/30 border border-cyan-800/40 p-2">
                      <div className="text-[9px] font-mono text-cyan-400 uppercase tracking-wider mb-1">Experimental</div>
                      <div className="text-lg font-bold font-mono text-cyan-300">{result.score_experimental.toFixed(1)}</div>
                      <div className="text-[9px] text-theme-muted">/ 100</div>
                    </div>
                  </div>

                  {/* Runtime */}
                  <div className="flex items-center justify-between text-[10px] text-theme-muted border-t border-theme pt-2">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span className="text-amber-400">{result.runtime_baseline_ms.toFixed(0)} ms</span>
                      <span className="mx-1">vs</span>
                      <span className="text-cyan-400">{result.runtime_experimental_ms.toFixed(0)} ms</span>
                    </div>
                    <span className="text-theme-muted">execution time</span>
                  </div>
                </div>

                {/* Error Curve */}
                <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2">
                  <h3 className="text-[11px] font-bold text-theme-secondary uppercase tracking-wide">Per-Frame Error Dynamics</h3>
                  <ErrorCurveChart
                    data={result.error_curve}
                    gapInterval={
                      activeTask === 'gap_filling' && result.config
                        ? [result.config.start_frame, result.config.end_frame]
                        : null
                    }
                  />
                </div>

                {/* Metrics Side-by-Side */}
                <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2.5">
                  <h3 className="text-[11px] font-bold text-theme-secondary uppercase tracking-wide">Metric Comparison</h3>
                  <div className="flex flex-col gap-1.5">
                    {Object.keys(result.metrics_baseline).filter(k => typeof result.metrics_baseline[k] === 'number').map((key) => {
                      const bVal = result.metrics_baseline[key] as number;
                      const eVal = result.metrics_experimental[key] as number;
                      const isLower = bVal > eVal;
                      return (
                        <div key={key} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                          <span className="text-[10px] text-theme-muted truncate font-mono">{key}</span>
                          <span className="text-[10px] font-mono text-amber-300">{bVal.toFixed(4)}</span>
                          <span className={`text-[10px] font-mono ${isLower ? 'text-emerald-400' : 'text-red-400'}`}>
                            {eVal.toFixed(4)}
                          </span>
                        </div>
                      );
                    })}
                    <div className="flex items-center justify-end gap-3 text-[9px] text-theme-muted mt-1 pt-1.5 border-t border-theme">
                      <span className="flex items-center gap-1"><span className="w-2 h-1 bg-amber-400 rounded inline-block" />Baseline</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-1 bg-cyan-400 rounded inline-block" />Experimental</span>
                    </div>
                  </div>
                </div>

                {/* Diagnostics */}
                {result.diagnostics && Object.keys(result.diagnostics).length > 0 && (
                  <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2">
                    <h3 className="text-[11px] font-bold text-theme-secondary uppercase tracking-wide flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-theme-muted" /> Diagnostics
                    </h3>
                    <div className="flex flex-col gap-1">
                      {Object.entries(result.diagnostics).map(([k, v]) => (
                        typeof v !== 'object' ? (
                          <div key={k} className="flex items-center justify-between">
                            <span className="text-[10px] font-mono text-theme-muted">{k}</span>
                            <span className="text-[10px] font-mono text-theme-secondary">
                              {typeof v === 'number' ? (v as number).toFixed(4) : String(v)}
                            </span>
                          </div>
                        ) : null
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        ) : (
          /* Benchmarks View */
          <div className="flex flex-col gap-3">
            {benchmarks ? (
              <>
                <div className="rounded-xl border border-theme bg-theme-card p-3">
                  <div className="text-[11px] font-bold text-theme-secondary uppercase tracking-wide mb-1">Benchmark Summary</div>
                  <div className="text-[10px] text-theme-muted">
                    Run: {benchmarks.timestamp} &mdash; Duration: {benchmarks.benchmark_duration_seconds}s
                  </div>
                  <div className="text-[10px] text-theme-muted mt-0.5">
                    Motions: {(benchmarks.motions_evaluated || []).join(', ')}
                  </div>
                </div>

                {/* T1 Summary */}
                <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2">
                  <div className="text-[11px] font-bold text-cyan-400 uppercase tracking-wide">Task 1 — Denoising</div>
                  <div className="grid grid-cols-2 gap-1 text-[10px]">
                    <div className="text-theme-muted">Method</div><div className="text-theme-muted text-right">Avg Score</div>
                    {Object.entries(benchmarks.task1_denoising as Record<string, any[]>).map(([m, entries]) => {
                      const avg = entries.reduce((s: number, e: any) => s + e.score, 0) / entries.length;
                      return (
                        <React.Fragment key={m}>
                          <span className="font-mono text-theme-secondary truncate">{m}</span>
                          <span className="font-mono text-right text-theme-secondary">{avg.toFixed(1)}</span>
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>

                {/* T2 Summary */}
                <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2">
                  <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wide">Task 2 — Gap Filling</div>
                  <div className="grid grid-cols-2 gap-1 text-[10px]">
                    <div className="text-theme-muted">Method</div><div className="text-theme-muted text-right">Avg Score</div>
                    {Object.entries(benchmarks.task2_gap_filling as Record<string, any[]>).map(([m, entries]) => {
                      const avg = entries.reduce((s: number, e: any) => s + e.score, 0) / entries.length;
                      return (
                        <React.Fragment key={m}>
                          <span className="font-mono text-theme-secondary truncate">{m}</span>
                          <span className="font-mono text-right text-theme-secondary">{avg.toFixed(1)}</span>
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>

                {/* T3 Summary */}
                <div className="rounded-xl border border-theme bg-theme-card p-3 flex flex-col gap-2">
                  <div className="text-[11px] font-bold text-purple-400 uppercase tracking-wide">Task 3 — Retargeting</div>
                  <div className="grid grid-cols-2 gap-1 text-[10px]">
                    <div className="text-theme-muted">Method</div><div className="text-theme-muted text-right">Avg Score</div>
                    {Object.entries(benchmarks.task3_retargeting as Record<string, any[]>).map(([m, entries]) => {
                      const avg = entries.reduce((s: number, e: any) => s + e.score, 0) / entries.length;
                      return (
                        <React.Fragment key={m}>
                          <span className="font-mono text-theme-secondary truncate">{m}</span>
                          <span className="font-mono text-right text-theme-secondary">{avg.toFixed(1)}</span>
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-theme-muted text-sm py-8">
                <Activity className="w-6 h-6 mx-auto mb-2 text-slate-600" />
                Benchmark results loading…
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
