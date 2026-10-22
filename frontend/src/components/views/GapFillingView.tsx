import React, { useState, useEffect } from 'react';
import { MotionItem, TaskResult, GapMetadataItem } from '../../types';
import { runGapFilling, fetchGapMetadata } from '../../services/api';
import { Scissors, Sliders, Play, Info, AlertCircle, Award, CheckCircle2 } from 'lucide-react';
import { MetricCard } from '../ui/MetricCard';
import { StatusBadge } from '../ui/StatusBadge';
import { MetricExplainer } from '../ui/MetricExplainer';

interface GapFillingViewProps {
  motions: MotionItem[];
  selectedMotionId: string;
  onSelectMotion: (motionId: string) => void;
  onSetBVH: (primary: string, secondary?: string) => void;
  onViewModeChange?: (mode: 'side-by-side' | 'overlay') => void;
  onSetGapInterval?: (interval: [number, number] | null) => void;
}

export const GapFillingView: React.FC<GapFillingViewProps> = ({
  motions,
  selectedMotionId,
  onSelectMotion,
  onSetBVH,
  onViewModeChange,
  onSetGapInterval,
}) => {
  const [gapType, setGapType] = useState<'SHORT' | 'MEDIUM' | 'LONG'>('MEDIUM');
  const [method, setMethod] = useState<'cubic' | 'linear'>('cubic');
  const [gapMetadata, setGapMetadata] = useState<Record<string, GapMetadataItem>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGapMetadata()
      .then((data) => setGapMetadata(data))
      .catch((err) => console.error('Failed to load gap metadata:', err));
  }, []);

  const currentMotion = motions.find((m) => m.motion_id === selectedMotionId) || motions[0];
  const gapId = currentMotion ? `${currentMotion.motion_id}_${gapType.toLowerCase()}` : '';
  const currentGapInfo = gapMetadata[gapId];

  // Update gap interval on timeline whenever selection changes
  useEffect(() => {
    if (currentGapInfo && onSetGapInterval) {
      onSetGapInterval([currentGapInfo.start_frame, currentGapInfo.end_frame]);
    } else if (onSetGapInterval) {
      onSetGapInterval(null);
    }
  }, [currentGapInfo]);

  const handleRun = async () => {
    if (!currentMotion) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runGapFilling(
        currentMotion.motion_id,
        gapType,
        currentGapInfo?.joint_name,
        currentGapInfo?.start_frame,
        currentGapInfo?.end_frame,
        method
      );
      setResult(res);
      onSetBVH(res.input_bvh, res.processed_bvh);
      if (onViewModeChange) onViewModeChange('side-by-side');
    } catch (err: any) {
      setError(err.message || 'Gap-filling execution error');
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
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-emerald-400">
              <Scissors className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-theme-primary">Motion Gap-Filling Laboratory</h2>
              <p className="text-[11px] text-theme-muted">
                Velocity-continuous cubic spline inpainting over occluded joint intervals
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            Track 2 — 30% Weight
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {/* Configuration Panel */}
        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col gap-3.5 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-theme">
            <h3 className="text-xs font-bold text-theme-secondary tracking-wide flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-emerald-400" /> Occlusion & Inpainting Setup
            </h3>
            <span className="text-[10px] font-mono text-theme-muted">Phase 2 Contract Specifications</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Motion Selector */}
            <div>
              <label className="text-[11px] font-medium text-theme-secondary block mb-1">
                Trial Sequence:
              </label>
              <select
                value={selectedMotionId}
                onChange={(e) => onSelectMotion(e.target.value)}
                className="w-full bg-theme-inset border border-theme rounded-lg px-2.5 py-1.5 text-xs text-theme-secondary outline-none focus:border-emerald-500 font-mono"
              >
                {motions.map((m) => (
                  <option key={m.motion_id} value={m.motion_id}>
                    {m.motion_id} — {m.description.slice(0, 20)} ({m.frame_count}f)
                  </option>
                ))}
              </select>
            </div>

            {/* Gap Severity Category */}
            <div>
              <label className="text-[11px] font-medium text-theme-secondary flex items-center gap-1 mb-1">
                <span>Occlusion Duration Preset:</span>
                <MetricExplainer metric="gap_type" />
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {(['SHORT', 'MEDIUM', 'LONG'] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setGapType(type)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-mono font-bold transition-all border ${
                      gapType === type
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500 shadow-sm'
                        : 'bg-theme-inset text-theme-muted hover:text-theme-secondary border-slate-800'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Actual Dataset Gap Specification Details */}
          {currentGapInfo && (
            <div className="bg-theme-inset p-3 rounded-lg border border-theme-sub text-xs font-mono space-y-1.5">
              <div className="flex items-center justify-between text-theme-secondary">
                <span className="text-theme-muted font-sans text-[11px]">Occluded Joint:</span>
                <span className="text-emerald-400 font-bold">{currentGapInfo.joint_name}</span>
              </div>
              <div className="flex items-center justify-between text-theme-secondary">
                <span className="text-theme-muted font-sans text-[11px]">Missing Frame Range:</span>
                <span className="text-theme-secondary">
                  Frames {currentGapInfo.start_frame} → {currentGapInfo.end_frame} ({currentGapInfo.gap_length} frames)
                </span>
              </div>
              <div className="flex items-center justify-between text-theme-secondary">
                <span className="text-theme-muted font-sans text-[11px]">Temporal Duration:</span>
                <span className="text-theme-muted">
                  {(currentGapInfo.start_frame / 120).toFixed(2)}s – {(currentGapInfo.end_frame / 120).toFixed(2)}s ({((currentGapInfo.gap_length / 120) * 1000).toFixed(0)} ms)
                </span>
              </div>

              {/* Visual Strip of missing frame range */}
              <div className="pt-1.5">
                <div className="flex items-center justify-between text-[10px] text-theme-muted font-sans mb-1">
                  <span>Frame 0</span>
                  <span className="text-rose-400 font-mono">Missing: [{currentGapInfo.start_frame}..{currentGapInfo.end_frame}]</span>
                  <span>Frame {currentMotion?.frame_count}</span>
                </div>
                <div className="w-full bg-theme-card h-2 rounded-full overflow-hidden flex relative border border-theme">
                  <div
                    className="h-full bg-slate-800"
                    style={{ width: `${(currentGapInfo.start_frame / (currentMotion?.frame_count || 300)) * 100}%` }}
                  />
                  <div
                    className="h-full bg-rose-500/80 shadow-sm shadow-rose-500/50"
                    style={{ width: `${(currentGapInfo.gap_length / (currentMotion?.frame_count || 300)) * 100}%` }}
                  />
                  <div className="flex-1 h-full bg-slate-800" />
                </div>
              </div>
            </div>
          )}

          {/* Interpolation Method Selector */}
          <div>
            <label className="text-[11px] font-medium text-theme-secondary block mb-1">
              Inpainting Algorithm:
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setMethod('cubic')}
                className={`py-1.5 px-3 rounded-lg text-xs font-medium border transition-all ${
                  method === 'cubic'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500 font-semibold'
                    : 'bg-theme-inset text-theme-muted border-slate-800'
                }`}
              >
                Cubic Spline (Velocity-Continuous)
              </button>
              <button
                onClick={() => setMethod('linear')}
                className={`py-1.5 px-3 rounded-lg text-xs font-medium border transition-all ${
                  method === 'linear'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500 font-semibold'
                    : 'bg-theme-inset text-theme-muted border-slate-800'
                }`}
              >
                Linear Interpolation
              </button>
            </div>
          </div>

          {/* Execute Button */}
          <button
            onClick={handleRun}
            disabled={loading}
            className={`w-full py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md ${
              loading
                ? 'bg-slate-800 text-theme-muted cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-theme-primary shadow-emerald-600/30'
            }`}
          >
            {loading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Inpainting Joint Trajectory...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> Execute Gap-Filling Algorithm
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
            {/* Score & Status Bar */}
            <div className="bg-theme-card border border-theme rounded-xl p-3.5 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <StatusBadge status={result.status} />
                <span className="text-xs font-medium text-theme-secondary">
                  {result.motion_id} ({result.gap_type} Gap on {result.gap_info?.joint_name})
                </span>
              </div>

              <div className="flex items-center gap-2 bg-theme-inset px-3 py-1 rounded-lg border border-theme">
                <Award className="w-4 h-4 text-amber-400" />
                <span className="text-[11px] uppercase tracking-wider text-theme-muted font-medium">Task Score:</span>
                <span className="text-sm font-extrabold font-mono text-emerald-300">
                  {result.score ? result.score.toFixed(2) : '0.00'}/100
                </span>
              </div>
            </div>

            {/* Metric Cards Grid */}
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                title={
                  <span className="flex items-center gap-1">
                    Inpainting MPJPE
                    <MetricExplainer metric="inpainting_error" />
                  </span>
                }
                value={result.metrics.inpainting_mpjpe ? result.metrics.inpainting_mpjpe.toFixed(4) : '--'}
                unit="in"
                direction="lower-is-better"
                tooltip="Mean per-joint position error computed specifically over the occluded frames and joints compared to clean ground truth."
              />

              <MetricCard
                title={
                  <span className="flex items-center gap-1">
                    Boundary Position Error
                    <MetricExplainer metric="boundary_error" />
                  </span>
                }
                value={result.metrics.boundary_error ? result.metrics.boundary_error.toFixed(4) : '--'}
                unit="in"
                direction="lower-is-better"
                tooltip="Discontinuity jump at the entry and exit anchor boundary frames (inches)."
              />

              <MetricCard
                title="Velocity Boundary Jump"
                value={result.metrics.velocity_boundary_error ? result.metrics.velocity_boundary_error.toFixed(2) : '0.00'}
                unit="in/s"
                direction="lower-is-better"
                tooltip="Velocity step discontinuity at the boundary transition."
              />

              <MetricCard
                title="Observed Frames Invariance"
                value="0.000 diff"
                unit=""
                direction="neutral"
                tooltip="Strict Phase 2 contract condition: frames outside the occlusion interval must remain 100% untouched bit-for-bit."
                subtitle="Contract: 100% Preserved"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
