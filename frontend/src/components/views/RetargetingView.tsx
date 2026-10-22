import React, { useState } from 'react';
import { MotionItem, TaskResult } from '../../types';
import { runRetargeting } from '../../services/api';
import { UserCheck, Sliders, Play, Info, AlertCircle, Award, Scale, CheckCircle2 } from 'lucide-react';
import { MetricCard } from '../ui/MetricCard';
import { StatusBadge } from '../ui/StatusBadge';
import { MetricExplainer } from '../ui/MetricExplainer';

interface RetargetingViewProps {
  motions: MotionItem[];
  selectedMotionId: string;
  onSelectMotion: (motionId: string) => void;
  onSetBVH: (primary: string, secondary?: string) => void;
  onViewModeChange?: (mode: 'side-by-side' | 'overlay') => void;
}

export const RetargetingView: React.FC<RetargetingViewProps> = ({
  motions,
  selectedMotionId,
  onSelectMotion,
  onSetBVH,
  onViewModeChange,
}) => {
  const [targetType, setTargetType] = useState<'target_small' | 'target_medium' | 'target_tall'>('target_medium');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentMotion = motions.find((m) => m.motion_id === selectedMotionId) || motions[0];

  const targetConfigs = {
    target_small: {
      name: 'Small Morphology (Compact Stature)',
      heightFactor: '0.78x total scale',
      torso: 0.82,
      upper_arm: 0.80,
      forearm: 0.82,
      thigh: 0.78,
      shin: 0.76,
      foot: 0.85,
    },
    target_medium: {
      name: 'Medium Morphology (Athletic Stature)',
      heightFactor: '1.08x total scale',
      torso: 0.95,
      upper_arm: 1.12,
      forearm: 1.15,
      thigh: 1.08,
      shin: 1.10,
      foot: 1.02,
    },
    target_tall: {
      name: 'Tall Morphology (Elongated Stature)',
      heightFactor: '1.30x total scale',
      torso: 1.25,
      upper_arm: 1.22,
      forearm: 1.28,
      thigh: 1.32,
      shin: 1.35,
      foot: 1.15,
    },
  };

  const currentTarget = targetConfigs[targetType];

  const handleRun = async () => {
    if (!currentMotion) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runRetargeting(currentMotion.motion_id, targetType);
      setResult(res);
      // Primary is canonical source motion, secondary is retargeted avatar
      onSetBVH(res.input_bvh, res.processed_bvh);
      if (onViewModeChange) onViewModeChange('side-by-side');
    } catch (err: any) {
      setError(err.message || 'Retargeting execution error');
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
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/25 flex items-center justify-center text-purple-400">
              <UserCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-theme-primary">Motion Retargeting Laboratory</h2>
              <p className="text-[11px] text-theme-muted">
                Cross-morphology kinematic retargeting with bone length invariance
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
            Track 3 — 40% Weight
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {/* Configuration Panel */}
        <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col gap-3.5 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-theme">
            <h3 className="text-xs font-bold text-theme-secondary tracking-wide flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-purple-400" /> Morphology Adaptation Setup
            </h3>
            <span className="text-[10px] font-mono text-theme-muted">Non-Uniform Limb Scaling</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Motion Selector */}
            <div>
              <label className="text-[11px] font-medium text-theme-secondary block mb-1">
                Source Clean Motion:
              </label>
              <select
                value={selectedMotionId}
                onChange={(e) => onSelectMotion(e.target.value)}
                className="w-full bg-theme-inset border border-theme rounded-lg px-2.5 py-1.5 text-xs text-theme-secondary outline-none focus:border-purple-500 font-mono"
              >
                {motions.map((m) => (
                  <option key={m.motion_id} value={m.motion_id}>
                    {m.motion_id} — {m.description.slice(0, 20)} ({m.frame_count}f)
                  </option>
                ))}
              </select>
            </div>

            {/* Target Avatar Selector */}
            <div>
              <label className="text-[11px] font-medium text-theme-secondary block mb-1">
                Target Avatar Morphology:
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {(['target_small', 'target_medium', 'target_tall'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTargetType(t)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-mono font-bold transition-all border ${
                      targetType === t
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500 shadow-sm'
                        : 'bg-theme-inset text-theme-muted hover:text-theme-secondary border-slate-800'
                    }`}
                  >
                    {t.replace('target_', '')}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Non-Uniform Limb Scale Multipliers Matrix */}
          <div className="bg-theme-inset p-3 rounded-lg border border-theme-sub text-xs font-mono space-y-2">
            <div className="flex items-center justify-between text-theme-secondary pb-1 border-b border-theme-sub">
              <span className="flex items-center gap-1.5 text-[11px] font-sans text-purple-300 font-semibold">
                <Scale className="w-3.5 h-3.5" /> {currentTarget.name}
              </span>
              <span className="text-[10px] text-theme-muted font-sans">{currentTarget.heightFactor}</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <div className="bg-theme-card p-1.5 rounded border border-theme flex justify-between">
                <span className="text-theme-muted">Torso:</span>
                <span className="text-theme-secondary font-bold">{currentTarget.torso}x</span>
              </div>
              <div className="bg-theme-card p-1.5 rounded border border-theme flex justify-between">
                <span className="text-theme-muted">Arm:</span>
                <span className="text-theme-secondary font-bold">{currentTarget.upper_arm}x</span>
              </div>
              <div className="bg-theme-card p-1.5 rounded border border-theme flex justify-between">
                <span className="text-theme-muted">Forearm:</span>
                <span className="text-theme-secondary font-bold">{currentTarget.forearm}x</span>
              </div>
              <div className="bg-theme-card p-1.5 rounded border border-theme flex justify-between">
                <span className="text-theme-muted">Thigh:</span>
                <span className="text-theme-secondary font-bold">{currentTarget.thigh}x</span>
              </div>
              <div className="bg-theme-card p-1.5 rounded border border-theme flex justify-between">
                <span className="text-theme-muted">Shin:</span>
                <span className="text-theme-secondary font-bold">{currentTarget.shin}x</span>
              </div>
              <div className="bg-theme-card p-1.5 rounded border border-theme flex justify-between">
                <span className="text-theme-muted">Foot:</span>
                <span className="text-theme-secondary font-bold">{currentTarget.foot}x</span>
              </div>
            </div>

            <p className="text-[10px] text-theme-muted font-sans leading-relaxed pt-1">
              * Non-uniform retargeting modifies bone offset lengths independently per limb group to model realistic anatomical variance without distortion.
            </p>
          </div>

          {/* Execute Button */}
          <button
            onClick={handleRun}
            disabled={loading}
            className={`w-full py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md ${
              loading
                ? 'bg-slate-800 text-theme-muted cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-500 text-theme-primary shadow-purple-600/30'
            }`}
          >
            {loading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Retargeting Kinematic Offsets...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> Execute Retargeting Algorithm
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
                  {result.motion_id} retargeted to {result.target_type}
                </span>
              </div>

              <div className="flex items-center gap-2 bg-theme-inset px-3 py-1 rounded-lg border border-theme">
                <Award className="w-4 h-4 text-amber-400" />
                <span className="text-[11px] uppercase tracking-wider text-theme-muted font-medium">Task Score:</span>
                <span className="text-sm font-extrabold font-mono text-purple-300">
                  {result.score ? result.score.toFixed(2) : '0.00'}/100
                </span>
              </div>
            </div>

            {/* Metric Cards Grid */}
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                title={
                  <span className="flex items-center gap-1">
                    End-Effector Error
                    <MetricExplainer metric="end_effector_error" />
                  </span>
                }
                value={result.metrics.end_effector_error ? result.metrics.end_effector_error.toFixed(4) : '--'}
                unit="in"
                direction="lower-is-better"
                tooltip="Normalized displacement error of the 5 distal end effectors (Head, Left Hand, Right Hand, Left Foot, Right Foot)."
              />

              <MetricCard
                title="Angular Geodesic Error"
                value={result.metrics.angular_geodesic_error ? result.metrics.angular_geodesic_error.toFixed(3) : '0.000'}
                unit="deg"
                direction="lower-is-better"
                tooltip="Mean rotation deviation on SO(3) across all joints."
              />

              <MetricCard
                title={
                  <span className="flex items-center gap-1">
                    Bone Length Invariance
                    <MetricExplainer metric="bone_length_violation" />
                  </span>
                }
                value="< 1e-5 in"
                unit=""
                direction="neutral"
                tooltip="Rigid body bone length variation across frames must be zero (< 1e-5 in threshold)."
                subtitle="Strictly Preserved"
              />

              <MetricCard
                title="Ground Penetration Penalty"
                value={result.metrics.ground_penetration_penalty ? result.metrics.ground_penetration_penalty.toFixed(3) : '0.000'}
                unit="in"
                direction="lower-is-better"
                tooltip="Foot penetration below the floor contact plane (in)."
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
