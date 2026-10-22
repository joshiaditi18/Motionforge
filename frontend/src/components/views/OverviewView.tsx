import React from 'react';
import { Sparkles, Scissors, UserCheck, ShieldCheck, Database, ArrowRight, Play, Cpu, CheckCircle2, Compass, Info } from 'lucide-react';
import { ActiveTab, MotionItem, RunnerResultSummary } from '../../types';
import { StatusBadge } from '../ui/StatusBadge';

interface OverviewViewProps {
  onNavigate: (tab: ActiveTab) => void;
  motions: MotionItem[];
  recentRuns?: RunnerResultSummary[];
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  onNavigate,
  motions,
  recentRuns = [],
}) => {
  const totalFrames = motions.reduce((acc, m) => acc + m.frame_count, 0) || 54560;

  return (
    <div className="p-6 max-w-6xl mx-auto flex flex-col gap-6" style={{ color: 'var(--text-primary)' }}>
      {/* Header Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-850 border border-theme p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col gap-2 max-w-2xl relative z-10">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[11px] font-mono font-semibold text-cyan-300 uppercase tracking-wider">
              Motion-Capture Processing & Evaluation Platform
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-theme-primary font-mono">
            MOTIONFORGE
          </h1>
          <p className="text-xs sm:text-sm text-theme-muted leading-relaxed">
            Clean. Complete. Retarget. A scientific motion-capture platform evaluating temporal denoising, missing marker gap inpainting, and cross-morphology kinematic retargeting with deterministic Phase 5 gatekeeping and Phase 4 evaluation.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0 relative z-10">
          <button
            onClick={() => onNavigate('demo')}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs tracking-wide uppercase transition-all shadow-sm shadow-violet-600/30 flex items-center justify-center gap-2"
          >
            <Compass className="w-3.5 h-3.5" /> Explore Demo
          </button>
          <button
            onClick={() => onNavigate('denoising')}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-theme-primary font-semibold text-xs tracking-wide uppercase transition-all shadow-sm shadow-cyan-600/30 flex items-center justify-center gap-2"
          >
            <Play className="w-3.5 h-3.5 fill-current" /> Start Denoising
          </button>
          <button
            onClick={() => onNavigate('motion-lab')}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-850 hover:bg-theme-hover text-theme-secondary font-semibold text-xs transition-all border border-theme-strong flex items-center justify-center gap-1.5"
          >
            <Database className="w-3.5 h-3.5 text-cyan-400" /> Explore {motions.length || 30} Motions
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-theme-muted">Total Motion Trials</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-theme-primary">{motions.length || 30}</span>
            <span className="text-[11px] text-theme-muted font-mono">21 Train / 9 Eval</span>
          </div>
          <div className="mt-2 text-[10px] text-theme-muted border-t border-theme pt-1.5 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Standardized CMU dataset
          </div>
        </div>

        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-theme-muted">Total Kinematic Frames</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-cyan-300">
              {totalFrames.toLocaleString()}
            </span>
            <span className="text-[11px] text-theme-muted font-mono">frames</span>
          </div>
          <div className="mt-2 text-[10px] text-theme-muted border-t border-theme pt-1.5 flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-400" /> 120.0 FPS (&Delta;t &asymp; 8.33 ms)
          </div>
        </div>

        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-theme-muted">Kinematic Channels</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-purple-300">96</span>
            <span className="text-[11px] text-theme-muted font-mono">channels</span>
          </div>
          <div className="mt-2 text-[10px] text-theme-muted border-t border-theme pt-1.5 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" /> 31 Functional Joints + 7 End Sites
          </div>
        </div>

        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-theme-muted">Competition Engine</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-400">Phase 6</span>
            <span className="text-[11px] text-theme-muted font-mono">Runner</span>
          </div>
          <div className="mt-2 text-[10px] text-theme-muted border-t border-theme pt-1.5 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" /> Phase 5 Security Gatekeeping
          </div>
        </div>
      </div>

      {/* Visual Pipeline Architecture */}
      <div className="bg-theme-card border border-theme rounded-xl p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between pb-2 border-b border-theme">
          <h3 className="text-xs font-bold text-theme-secondary uppercase tracking-wider flex items-center gap-2">
            <span>Evaluation & Verification Pipeline</span>
          </h3>
          <span className="text-[10px] font-mono text-theme-muted">Phase 4/5/6 Deterministic Architecture</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-2">
          <div className="bg-theme-inset p-3 rounded-lg border border-theme-sub flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-theme-muted font-bold uppercase">Stage 1</span>
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
              </div>
              <h4 className="text-xs font-bold text-theme-secondary">Input Motions</h4>
              <p className="text-[11px] text-theme-muted mt-1 leading-snug">
                Raw CMU optical sequences with injected noise, missing joint intervals, or target avatar requirements.
              </p>
            </div>
          </div>

          <div className="bg-theme-inset p-3 rounded-lg border border-theme-sub flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-theme-muted font-bold uppercase">Stage 2</span>
                <span className="w-2 h-2 rounded-full bg-indigo-400" />
              </div>
              <h4 className="text-xs font-bold text-theme-secondary">Algorithm Execution</h4>
              <p className="text-[11px] text-theme-muted mt-1 leading-snug">
                Phase-unwrapped Savitzky-Golay filtering, velocity-continuous cubic inpainting, or proportional retargeting.
              </p>
            </div>
          </div>

          <div className="bg-theme-inset p-3 rounded-lg border border-theme-sub flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-theme-muted font-bold uppercase">Stage 3</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
              </div>
              <h4 className="text-xs font-bold text-theme-secondary">Phase 5 Validator</h4>
              <p className="text-[11px] text-theme-muted mt-1 leading-snug">
                Deterministic security audit: archive integrity, safe extraction, hierarchy check, frame count, 120 FPS.
              </p>
            </div>
          </div>

          <div className="bg-theme-inset p-3 rounded-lg border border-theme-sub flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-theme-muted font-bold uppercase">Stage 4</span>
                <span className="w-2 h-2 rounded-full bg-amber-400" />
              </div>
              <h4 className="text-xs font-bold text-theme-secondary">Phase 4 Scorer</h4>
              <p className="text-[11px] text-theme-muted mt-1 leading-snug">
                Official FK error evaluation, calibrated exponential decay normalization ($\tau$), composite 30/30/40 scoring.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Three Competition Tracks Cards */}
      <div>
        <h3 className="text-xs font-bold text-theme-secondary uppercase tracking-wider mb-3">
          Competition Tracks & Calibrated Baselines
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Task 1 */}
          <div
            onClick={() => onNavigate('denoising')}
            className="group cursor-pointer bg-theme-card hover:bg-theme-hover transition-all border border-theme hover:border-cyan-500/50 rounded-xl p-4 flex flex-col justify-between shadow-md"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                  30% Weight
                </span>
              </div>
              <h4 className="text-sm font-bold text-theme-primary group-hover:text-cyan-300 transition-colors">
                Track 1: Denoising
              </h4>
              <p className="text-xs text-theme-muted mt-1 leading-relaxed">
                Filters synthetic Gaussian jitter while preserving deliberate motion dynamics.
              </p>

              <div className="mt-3 bg-theme-inset p-2.5 rounded-lg border border-theme-sub text-[10px] font-mono space-y-1">
                <div className="flex justify-between text-theme-muted">
                  <span>Calibrated Medians:</span>
                  <span className="text-theme-secondary font-bold">L: 60.4 | M: 40.0 | H: 15.0</span>
                </div>
                <div className="flex justify-between text-theme-muted">
                  <span>Intra-Task Weights:</span>
                  <span className="text-cyan-400">MPJPE 40% / Vel 30% / Jitter 30%</span>
                </div>
              </div>
            </div>

            <div className="mt-3 pt-2.5 border-t border-theme flex items-center justify-between text-[11px] text-cyan-400 font-medium">
              <span>Open Denoising Workbench</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Task 2 */}
          <div
            onClick={() => onNavigate('gap-filling')}
            className="group cursor-pointer bg-theme-card hover:bg-theme-hover transition-all border border-theme hover:border-emerald-500/50 rounded-xl p-4 flex flex-col justify-between shadow-md"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <Scissors className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                  30% Weight
                </span>
              </div>
              <h4 className="text-sm font-bold text-theme-primary group-hover:text-emerald-300 transition-colors">
                Track 2: Gap Filling
              </h4>
              <p className="text-xs text-theme-muted mt-1 leading-relaxed">
                Reconstructs missing rotations over marker occlusion intervals with boundary velocity matching.
              </p>

              <div className="mt-3 bg-theme-inset p-2.5 rounded-lg border border-theme-sub text-[10px] font-mono space-y-1">
                <div className="flex justify-between text-theme-muted">
                  <span>Calibrated Medians:</span>
                  <span className="text-theme-secondary font-bold">S: 51.8 | M: 62.8 | L: 12.5</span>
                </div>
                <div className="flex justify-between text-theme-muted">
                  <span>Observed Frames:</span>
                  <span className="text-emerald-400 font-semibold">Strictly Untouched (0.00 diff)</span>
                </div>
              </div>
            </div>

            <div className="mt-3 pt-2.5 border-t border-theme flex items-center justify-between text-[11px] text-emerald-400 font-medium">
              <span>Open Gap-Filling Workbench</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Task 3 */}
          <div
            onClick={() => onNavigate('retargeting')}
            className="group cursor-pointer bg-theme-card hover:bg-theme-hover transition-all border border-theme hover:border-purple-500/50 rounded-xl p-4 flex flex-col justify-between shadow-md"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <UserCheck className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                  40% Weight
                </span>
              </div>
              <h4 className="text-sm font-bold text-theme-primary group-hover:text-purple-300 transition-colors">
                Track 3: Retargeting
              </h4>
              <p className="text-xs text-theme-muted mt-1 leading-relaxed">
                Adapts motion to non-uniform avatar morphologies with bone length invariance.
              </p>

              <div className="mt-3 bg-theme-inset p-2.5 rounded-lg border border-theme-sub text-[10px] font-mono space-y-1">
                <div className="flex justify-between text-theme-muted">
                  <span>Calibrated Medians:</span>
                  <span className="text-theme-secondary font-bold">S: 43.2 | M: 66.8 | T: 68.3</span>
                </div>
                <div className="flex justify-between text-theme-muted">
                  <span>Bone Invariance:</span>
                  <span className="text-purple-400">&lt; 1e-5 in threshold</span>
                </div>
              </div>
            </div>

            <div className="mt-3 pt-2.5 border-t border-theme flex items-center justify-between text-[11px] text-purple-400 font-medium">
              <span>Open Retargeting Workbench</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Runner Artifacts (if any exist) */}
      {recentRuns && recentRuns.length > 0 && (
        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between pb-2 border-b border-theme">
            <h3 className="text-xs font-bold text-theme-secondary uppercase tracking-wider">
              Recent Local Competition Runs
            </h3>
            <button
              onClick={() => onNavigate('competition')}
              className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
            >
              View Competition Studio <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2">
            {recentRuns.slice(0, 3).map((run) => (
              <div
                key={run.job_id}
                onClick={() => onNavigate('competition')}
                className="bg-theme-inset p-2.5 rounded-lg border border-theme-sub flex items-center justify-between cursor-pointer hover:bg-theme-card transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-theme-secondary">
                    Job {run.job_id.slice(0, 8)}
                  </span>
                  <StatusBadge status={run.status} size="sm" />
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  {run.overall_score !== null && run.overall_score !== undefined ? (
                    <span className="text-cyan-300 font-bold">
                      Score: {run.overall_score.toFixed(2)}/100
                    </span>
                  ) : (
                    <span className="text-theme-muted">Evaluation Finished</span>
                  )}
                  <span className="text-[10px] text-theme-muted">{run.file}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
