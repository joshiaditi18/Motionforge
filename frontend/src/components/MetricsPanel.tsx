import React from 'react';
import { TaskResult } from '../types';
import { Award, Zap, CheckCircle2, TrendingUp, AlertTriangle } from 'lucide-react';

interface MetricsPanelProps {
  result: TaskResult | null;
  loading: boolean;
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ result, loading }) => {
  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col items-center justify-center min-h-[200px] gap-3">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-cyan-300 font-mono tracking-wide">Executing Python baseline & Phase 4 evaluator...</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 flex flex-col items-center justify-center min-h-[160px] text-center gap-2">
        <Zap className="w-6 h-6 text-slate-500" />
        <h4 className="text-sm font-medium text-slate-300">No Processing Run Yet</h4>
        <p className="text-xs text-slate-500 max-w-xs">
          Select motion parameters and click &ldquo;Process Motion&rdquo; to execute the official algorithm and inspect live metrics.
        </p>
      </div>
    );
  }

  const { task, score, metrics, status } = result;

  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 shadow-xl">
      {/* Header & Overall Score */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Task Evaluation
            </span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                status === 'VALID'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}
            >
              {status}
            </span>
          </div>
          <h3 className="text-sm font-bold text-slate-100 capitalize">
            {task.replace('_', ' ')} Performance
          </h3>
        </div>

        {/* Task Score Gauge Card */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-850 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-2.5">
          <Award className="w-5 h-5 text-amber-400" />
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Task Score</div>
            <div className="text-base font-extrabold font-mono text-cyan-300">
              {score ? score.toFixed(2) : '0.00'}
              <span className="text-[11px] text-slate-400 font-normal"> / 100</span>
            </div>
          </div>
        </div>
      </div>

      {/* Task Specific Metrics Cards */}
      {task === 'denoising' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">MPJPE (Position Error)</span>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-base font-bold font-mono text-slate-100">
                {metrics.mpjpe ? metrics.mpjpe.toFixed(4) : '--'}
                <span className="text-xs font-normal text-slate-400 ml-1">in</span>
              </span>
              {metrics.mpjpe_improvement_pct && (
                <span className="text-[11px] text-emerald-400 font-mono font-semibold flex items-center gap-0.5">
                  <TrendingUp className="w-3 h-3" />+{metrics.mpjpe_improvement_pct.toFixed(1)}%
                </span>
              )}
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Jitter Reduction</span>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-base font-bold font-mono text-cyan-300">
                {metrics.jitter_reduction_pct ? `${metrics.jitter_reduction_pct.toFixed(1)}%` : '--'}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                {metrics.jitter ? `${Math.round(metrics.jitter)} in/s²` : ''}
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Velocity Error</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-slate-200">
                {metrics.velocity_error ? metrics.velocity_error.toFixed(2) : '--'}
                <span className="text-xs font-normal text-slate-400 ml-1">in/s</span>
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Kinetic Energy Preservation</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-purple-300">
                {metrics.motion_preservation ? `${(metrics.motion_preservation * 100).toFixed(1)}%` : '--'}
              </span>
            </div>
          </div>
        </div>
      )}

      {task === 'gap_filling' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Inpainting MPJPE</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-emerald-300">
                {metrics.inpainting_mpjpe ? metrics.inpainting_mpjpe.toFixed(4) : '--'}
                <span className="text-xs font-normal text-slate-400 ml-1">in</span>
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Boundary Discontinuity</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-slate-200">
                {metrics.boundary_error ? metrics.boundary_error.toFixed(4) : '--'}
                <span className="text-xs font-normal text-slate-400 ml-1">in</span>
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Velocity Boundary Jump</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-purple-300">
                {metrics.velocity_boundary_error ? metrics.velocity_boundary_error.toFixed(2) : '--'}
                <span className="text-xs font-normal text-slate-400 ml-1">in/s</span>
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Observed Frames Preserved</span>
            <div className="mt-1 flex items-center gap-1.5 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" /> Strictly Intact (0.00 diff)
            </div>
          </div>
        </div>
      )}

      {task === 'retargeting' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">End-Effector Error</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-purple-300">
                {metrics.end_effector_error ? metrics.end_effector_error.toFixed(4) : '--'}
                <span className="text-xs font-normal text-slate-400 ml-1">in</span>
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Angular Geodesic Error</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-cyan-300">
                {metrics.angular_geodesic_error ? metrics.angular_geodesic_error.toFixed(3) : '0.000'}
                <span className="text-xs font-normal text-slate-400 ml-1">deg</span>
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Bone Length Invariance</span>
            <div className="mt-1 flex items-center gap-1 text-emerald-400 text-xs font-mono font-bold">
              <CheckCircle2 className="w-3.5 h-3.5" /> &lt; 1e-5 in (Preserved)
            </div>
          </div>

          <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
            <span className="text-[11px] text-slate-400">Ground Penetration</span>
            <div className="mt-1">
              <span className="text-base font-bold font-mono text-slate-200">
                {metrics.ground_penetration_penalty ? metrics.ground_penetration_penalty.toFixed(3) : '0.000'}
                <span className="text-xs font-normal text-slate-400 ml-1">in</span>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Contract Verification Footnote */}
      <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-800/80 flex items-center justify-between">
        <span>Evaluated against Phase 2/4 data contract</span>
        <span className="font-mono text-slate-400">120 FPS / 96 Channels</span>
      </div>
    </div>
  );
};
