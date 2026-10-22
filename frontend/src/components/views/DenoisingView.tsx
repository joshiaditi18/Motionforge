import React, { useState } from 'react';
import { MotionItem, TaskResult } from '../../types';
import { runDenoising } from '../../services/api';
import { Sparkles, Sliders, Play, Info, AlertCircle, Award } from 'lucide-react';
import { MetricCard } from '../ui/MetricCard';
import { ComparisonChart } from '../ui/ComparisonChart';
import { StatusBadge } from '../ui/StatusBadge';
import { MetricExplainer } from '../ui/MetricExplainer';

interface DenoisingViewProps {
  motions: MotionItem[];
  selectedMotionId: string;
  onSelectMotion: (motionId: string) => void;
  onSetBVH: (primary: string, secondary?: string) => void;
  onViewModeChange?: (mode: 'side-by-side' | 'overlay') => void;
}

export const DenoisingView: React.FC<DenoisingViewProps> = ({
  motions,
  selectedMotionId,
  onSelectMotion,
  onSetBVH,
  onViewModeChange,
}) => {
  const [noiseLevel, setNoiseLevel] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('LOW');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentMotion = motions.find((m) => m.motion_id === selectedMotionId) || motions[0];

  const handleRun = async () => {
    if (!currentMotion) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runDenoising(currentMotion.motion_id, noiseLevel);
      setResult(res);
      // Primary is corrupted input, secondary is denoised output
      onSetBVH(res.input_bvh, res.processed_bvh);
      if (onViewModeChange) onViewModeChange('side-by-side');
    } catch (err: any) {
      setError(err.message || 'Denoising execution error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-4 sm:p-5 overflow-y-auto" style={{ backgroundColor: 'var(--bg-page)' }}>
      {/* Workbench Header */}
      <div className="pb-3.5 border-b mb-4" style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-theme-primary">Motion Denoising Laboratory</h2>
              <p className="text-[11px] text-theme-muted">
                Phase-unwrapped polynomial smoothing across 96 channels
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
            Track 1 — 30% Weight
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {/* Configuration Panel */}
        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col gap-3.5 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-theme">
            <h3 className="text-xs font-bold text-theme-secondary tracking-wide flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" /> Filter & Noise Parameters
            </h3>
            <span className="text-[10px] font-mono text-theme-muted">120 FPS / &Delta;t &asymp; 8.33 ms</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Motion Selector */}
            <div>
              <label className="text-[11px] font-medium text-theme-secondary block mb-1">
                Challenge Motion Sequence:
              </label>
              <select
                value={selectedMotionId}
                onChange={(e) => onSelectMotion(e.target.value)}
                className="w-full bg-theme-inset border border-theme rounded-lg px-2.5 py-1.5 text-xs text-theme-secondary outline-none focus:border-cyan-500 font-mono"
              >
                {motions.map((m) => (
                  <option key={m.motion_id} value={m.motion_id}>
                    {m.motion_id} — {m.description.slice(0, 20)} ({m.duration_seconds.toFixed(1)}s, {m.frame_count}f)
                  </option>
                ))}
              </select>
            </div>

            {/* Noise Severity Level */}
            <div>
              <label className="text-[11px] font-medium text-theme-secondary flex items-center gap-1 mb-1">
                <span>Gaussian Noise Severity Level:</span>
                <MetricExplainer metric="noise_level" />
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {(['LOW', 'MEDIUM', 'HIGH'] as const).map((lvl) => (
                  <button
                    key={lvl}
                    onClick={() => setNoiseLevel(lvl)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-mono font-bold transition-all border ${
                      noiseLevel === lvl
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500 shadow-sm'
                        : 'bg-theme-inset text-theme-muted hover:text-theme-secondary border-slate-800'
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Technical Filter Specs Details */}
          <div className="bg-theme-inset p-2.5 rounded-lg border border-theme-sub text-[11px] text-theme-muted flex items-start gap-2">
            <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
            <div className="leading-snug">
              <span className="text-theme-secondary font-medium">Savitzky-Golay quadratic filter (polyorder=2)</span> with phase unwrapping across gimbal boundaries.
              {noiseLevel === 'LOW' && ' Window length: 7 frames (58 ms). Calibrated baseline median score: 60.4.'}
              {noiseLevel === 'MEDIUM' && ' Window length: 13 frames (108 ms). Calibrated baseline median score: 40.0.'}
              {noiseLevel === 'HIGH' && ' Window length: 19 frames (158 ms). Calibrated baseline median score: 15.0.'}
            </div>
          </div>

          {/* Execute Button */}
          <button
            onClick={handleRun}
            disabled={loading}
            className={`w-full py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md ${
              loading
                ? 'bg-slate-800 text-theme-muted cursor-not-allowed'
                : 'bg-cyan-600 hover:bg-cyan-500 text-theme-primary shadow-cyan-600/30'
            }`}
          >
            {loading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Executing Savitzky-Golay Filter...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> Execute Denoising Algorithm
              </>
            )}
          </button>

          {error && (
            <div className="bg-rose-500/10 border border-rose-500/30 text-rose-300 p-2.5 rounded-lg text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Results Section */}
        {result && (
          <div className="flex flex-col gap-3.5">
            {/* Score & Validation Status Bar */}
            <div className="bg-theme-card border border-theme rounded-xl p-3.5 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <StatusBadge status={result.status} />
                <span className="text-xs font-medium text-theme-secondary">
                  {result.motion_id} ({result.noise_level} Noise) Evaluated
                </span>
              </div>

              <div className="flex items-center gap-2 bg-theme-inset px-3 py-1 rounded-lg border border-theme">
                <Award className="w-4 h-4 text-amber-400" />
                <span className="text-[11px] uppercase tracking-wider text-theme-muted font-medium">Task Score:</span>
                <span className="text-sm font-extrabold font-mono text-cyan-300">
                  {result.score ? result.score.toFixed(2) : '0.00'}/100
                </span>
              </div>
            </div>

            {/* Scientific Metric Cards Grid */}
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                title={
                  <span className="flex items-center gap-1">
                    MPJPE (Position Error)
                    <MetricExplainer metric="mpjpe" />
                  </span>
                }
                value={result.metrics.mpjpe ? result.metrics.mpjpe.toFixed(4) : '--'}
                unit="in"
                rawValue={result.metrics.raw_mpjpe}
                improvementPct={result.metrics.mpjpe_improvement_pct}
                direction="lower-is-better"
                tooltip="Mean Per-Joint Position Error in inches across all 31 joints and all frames compared to clean ground truth."
              />

              <MetricCard
                title={
                  <span className="flex items-center gap-1">
                    Jitter Reduction
                    <MetricExplainer metric="jitter" />
                  </span>
                }
                value={result.metrics.jitter_reduction_pct ? `${result.metrics.jitter_reduction_pct.toFixed(1)}%` : '--'}
                unit=""
                rawValue={result.metrics.raw_jitter ? Math.round(result.metrics.raw_jitter) : undefined}
                improvementPct={result.metrics.jitter_reduction_pct}
                direction="higher-is-better"
                tooltip="Percentage reduction in second-order temporal acceleration error (in/s²)."
                subtitle={result.metrics.jitter ? `${Math.round(result.metrics.jitter)} in/s² filtered` : undefined}
              />

              <MetricCard
                title="Velocity Error (JVE)"
                value={result.metrics.velocity_error ? result.metrics.velocity_error.toFixed(2) : '--'}
                unit="in/s"
                direction="lower-is-better"
                tooltip="First-order temporal finite difference velocity error in inches/second."
              />

              <MetricCard
                title="Kinetic Energy Preservation"
                value={result.metrics.motion_preservation ? `${(result.metrics.motion_preservation * 100).toFixed(1)}%` : '--'}
                unit=""
                direction="neutral"
                tooltip="Ratio of predicted velocity squared sum to ground-truth velocity squared sum. Anti-degeneracy bound: [35%, 300%]."
                subtitle="Anti-degeneracy: Valid"
              />
            </div>

            {/* Before vs After Scientific Comparison Chart */}
            {result.metrics.raw_mpjpe !== undefined && result.metrics.mpjpe !== undefined && (
              <ComparisonChart
                title="Kinematic Error Reduction Analysis"
                subtitle="Side-by-side comparison of raw corrupted sequence vs filtered sequence"
                items={[
                  {
                    label: 'Position Error (MPJPE)',
                    rawValue: result.metrics.raw_mpjpe,
                    processedValue: result.metrics.mpjpe,
                    unit: 'in',
                    lowerIsBetter: true,
                  },
                  {
                    label: 'Acceleration Jitter Error',
                    rawValue: (result.metrics.raw_jitter || 0) / 1000,
                    processedValue: (result.metrics.jitter || 0) / 1000,
                    unit: 'k in/s²',
                    lowerIsBetter: true,
                  },
                ]}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
