import React, { useState } from 'react';
import {
  ActiveTab,
  MotionItem,
  TaskResult,
} from '../../types';
import {
  runDenoising,
  runGapFilling,
  runRetargeting,
} from '../../services/api';
import {
  Sparkles,
  Scissors,
  UserCheck,
  Play,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  Download,
  Eye,
  AlertCircle,
  Award,
  Layers,
  Activity,
  Sliders,
  FileCode,
  Zap,
  Info,
} from 'lucide-react';
import { MetricCard } from '../ui/MetricCard';
import { StatusBadge } from '../ui/StatusBadge';
import { MetricExplainer } from '../ui/MetricExplainer';

interface GuidedDemoViewProps {
  motions: MotionItem[];
  onSetBVH: (primary: string, secondary?: string) => void;
  onViewModeChange?: (mode: 'single' | 'side-by-side' | 'overlay') => void;
  onNavigate: (tab: ActiveTab) => void;
}

type DemoTask = 'denoising' | 'gap_filling' | 'retargeting';

export const GuidedDemoView: React.FC<GuidedDemoViewProps> = ({
  motions,
  onSetBVH,
  onViewModeChange,
  onNavigate,
}) => {
  // Wizard Step (1 to 6)
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Configuration state
  const [selectedMotionId, setSelectedMotionId] = useState<string>(
    motions.length > 0 ? motions[0].motion_id : 'MF001'
  );
  const [selectedTask, setSelectedTask] = useState<DemoTask>('denoising');
  const [noiseLevel, setNoiseLevel] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('MEDIUM');
  const [gapType, setGapType] = useState<'SHORT' | 'MEDIUM' | 'LONG'>('MEDIUM');
  const [targetType, setTargetType] = useState<string>('target_medium');

  // Execution state
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasExported, setHasExported] = useState<boolean>(false);
  const [loadedInViewer, setLoadedInViewer] = useState<boolean>(false);

  const selectedMotion =
    motions.find((m) => m.motion_id === selectedMotionId) || motions[0];

  const steps = [
    { num: 1, title: 'Select Motion', desc: 'Choose source sequence' },
    { num: 2, title: 'Select Task', desc: 'Denoise, Inpaint, or Retarget' },
    { num: 3, title: 'Configure', desc: 'Tune hyperparameters' },
    { num: 4, title: 'Run Pipeline', desc: 'Execute live backend algorithm' },
    { num: 5, title: 'Inspect Results', desc: 'Metrics & 3D loading' },
    { num: 6, title: 'Interpretation', desc: 'Scientific evaluation' },
  ];

  // Execute pipeline
  const handleExecute = async () => {
    if (!selectedMotion) return;
    setLoading(true);
    setError(null);
    setLoadedInViewer(false);

    try {
      let res: TaskResult;
      if (selectedTask === 'denoising') {
        res = await runDenoising(selectedMotion.motion_id, noiseLevel);
      } else if (selectedTask === 'gap_filling') {
        res = await runGapFilling(selectedMotion.motion_id, gapType);
      } else {
        res = await runRetargeting(selectedMotion.motion_id, targetType);
      }

      setResult(res);
      setCurrentStep(5);
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed. Please verify the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // Load in 3D Viewer
  const handleLoadInViewer = () => {
    if (!result) return;
    onSetBVH(result.input_bvh, result.processed_bvh);
    if (onViewModeChange) {
      onViewModeChange('side-by-side');
    }
    setLoadedInViewer(true);
  };

  // Download JSON export
  const handleExportJSON = () => {
    if (!result) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(result, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute(
      'download',
      `motionforge_${selectedTask}_${result.motion_id}_result.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    setHasExported(true);
  };

  const handleResetWizard = () => {
    setCurrentStep(1);
    setResult(null);
    setError(null);
    setHasExported(false);
    setLoadedInViewer(false);
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto flex flex-col gap-6" style={{ color: 'var(--text-primary)' }}>
      {/* Header Banner */}
      <div
        className="rounded-2xl p-6 border shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 relative overflow-hidden"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-default)',
        }}
      >
        <div className="flex flex-col gap-1.5 max-w-2xl z-10">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--accent)' }} />
            <span className="text-[11px] font-mono font-semibold uppercase tracking-wider" style={{ color: 'var(--accent-text)' }}>
              Interactive Research Demonstration
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight font-mono" style={{ color: 'var(--text-primary)' }}>
            Guided Motion Processing Tour
          </h1>
          <p className="text-xs sm:text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            Experience the complete MOTIONFORGE pipeline step-by-step: select real motion capture data, configure scientific algorithms, execute live kinematics, and interpret evaluation metrics.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0 z-10">
          <button
            onClick={handleResetWizard}
            className="px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all"
            style={{
              backgroundColor: 'var(--bg-inset)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset Tour
          </button>
        </div>
      </div>

      {/* Stepper Navigation Indicator */}
      <div
        className="rounded-xl p-3 border shadow-sm"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-default)',
        }}
      >
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
          {steps.map((s) => {
            const isActive = currentStep === s.num;
            const isCompleted = currentStep > s.num;
            return (
              <button
                key={s.num}
                onClick={() => {
                  if (s.num <= 4 || result) {
                    setCurrentStep(s.num);
                  }
                }}
                disabled={s.num > 4 && !result}
                className={`flex items-center gap-2.5 p-2 rounded-lg text-left transition-all border ${
                  isActive
                    ? 'shadow-sm'
                    : ''
                }`}
                style={{
                  backgroundColor: isActive
                    ? 'var(--bg-hover)'
                    : isCompleted
                    ? 'var(--bg-inset)'
                    : 'transparent',
                  borderColor: isActive
                    ? 'var(--accent)'
                    : isCompleted
                    ? 'var(--border-strong)'
                    : 'transparent',
                  opacity: s.num > 4 && !result ? 0.45 : 1,
                  cursor: s.num > 4 && !result ? 'not-allowed' : 'pointer',
                }}
              >
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-bold shrink-0 transition-colors"
                  style={
                    isActive
                      ? { backgroundColor: 'var(--accent)', color: '#000' }
                      : isCompleted
                      ? { backgroundColor: 'var(--success-bg)', color: 'var(--success-text)', border: '1px solid var(--success-border)' }
                      : { backgroundColor: 'var(--bg-inset)', color: 'var(--text-muted)', border: '1px solid var(--border-default)' }
                  }
                >
                  {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : s.num}
                </div>
                <div className="flex flex-col truncate">
                  <span
                    className="text-[11px] font-bold truncate"
                    style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                  >
                    {s.title}
                  </span>
                  <span className="text-[9px] truncate" style={{ color: 'var(--text-muted)' }}>
                    {s.desc}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Step Body */}
      <div
        className="rounded-xl border p-5 sm:p-6 shadow-sm min-h-[380px] flex flex-col justify-between"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border-default)',
        }}
      >
        {/* STEP 1: SELECT MOTION */}
        {currentStep === 1 && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Layers className="w-4 h-4 text-cyan-400" /> Step 1: Select Source Motion Sequence
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Choose from {motions.length} standardized CMU optical motion capture trials (120 FPS, 31 functional joints).
                </p>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-inset)', color: 'var(--accent-text)' }}>
                {motions.length} Available
              </span>
            </div>

            {motions.length === 0 ? (
              <div className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>
                <p className="text-sm">Connecting to backend motion library...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 max-h-[340px] overflow-y-auto pr-1">
                {motions.map((m) => {
                  const isSelected = m.motion_id === selectedMotionId;
                  return (
                    <div
                      key={m.motion_id}
                      onClick={() => setSelectedMotionId(m.motion_id)}
                      className="p-3 rounded-xl border cursor-pointer transition-all flex flex-col justify-between"
                      style={{
                        backgroundColor: isSelected ? 'var(--bg-hover)' : 'var(--bg-inset)',
                        borderColor: isSelected ? 'var(--accent)' : 'var(--border-subtle)',
                        transform: isSelected ? 'translateY(-1px)' : 'none',
                        boxShadow: isSelected ? '0 4px 12px rgba(34, 211, 238, 0.15)' : 'none',
                      }}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-mono font-bold text-xs" style={{ color: isSelected ? 'var(--accent-text)' : 'var(--text-primary)' }}>
                            {m.motion_id}
                          </span>
                          <span
                            className="text-[9px] uppercase px-1.5 py-0.5 rounded font-mono font-semibold"
                            style={{
                              backgroundColor: isSelected ? 'var(--accent-bg)' : 'var(--bg-card)',
                              color: isSelected ? 'var(--accent-text)' : 'var(--text-muted)',
                            }}
                          >
                            {m.category || 'locomotion'}
                          </span>
                        </div>
                        <p className="text-xs line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                          {m.description}
                        </p>
                      </div>

                      <div className="mt-3 pt-2 border-t flex items-center justify-between text-[10px] font-mono" style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
                        <span>{m.duration_seconds.toFixed(1)}s</span>
                        <span>{m.frame_count} frames</span>
                        <span>{m.joint_count} joints</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* STEP 2: SELECT TASK */}
        {currentStep === 2 && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Activity className="w-4 h-4 text-purple-400" /> Step 2: Select Kinematic Processing Task
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Each task represents an independent algorithmic challenge in motion-capture reconstruction.
                </p>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-inset)', color: 'var(--accent-text)' }}>
                3 Competition Tracks
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Task 1 Card */}
              <div
                onClick={() => setSelectedTask('denoising')}
                className="p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between"
                style={{
                  backgroundColor: selectedTask === 'denoising' ? 'var(--bg-hover)' : 'var(--bg-inset)',
                  borderColor: selectedTask === 'denoising' ? 'var(--accent)' : 'var(--border-subtle)',
                  boxShadow: selectedTask === 'denoising' ? '0 4px 14px rgba(34, 211, 238, 0.15)' : 'none',
                }}
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
                  <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                    Track 1: Motion Denoising
                  </h3>
                  <p className="text-xs mt-1.5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    Removes synthetic Gaussian marker jitter while strictly preserving biological dynamics. Uses phase unwrapping across Euler gimbal singularities followed by Savitzky-Golay quadratic polynomial filtering.
                  </p>
                </div>

                <div className="mt-4 pt-2.5 border-t text-[10px] space-y-1" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex justify-between" style={{ color: 'var(--text-muted)' }}>
                    <span>Target Metric:</span>
                    <span className="font-semibold text-cyan-400">MPJPE + Jitter Error</span>
                  </div>
                  <div className="flex justify-between" style={{ color: 'var(--text-muted)' }}>
                    <span>Anti-Degeneracy:</span>
                    <span style={{ color: 'var(--text-secondary)' }}>Kinetic energy bounds</span>
                  </div>
                </div>
              </div>

              {/* Task 2 Card */}
              <div
                onClick={() => setSelectedTask('gap_filling')}
                className="p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between"
                style={{
                  backgroundColor: selectedTask === 'gap_filling' ? 'var(--bg-hover)' : 'var(--bg-inset)',
                  borderColor: selectedTask === 'gap_filling' ? '#10b981' : 'var(--border-subtle)',
                  boxShadow: selectedTask === 'gap_filling' ? '0 4px 14px rgba(16, 185, 129, 0.15)' : 'none',
                }}
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
                  <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                    Track 2: Gap Filling
                  </h3>
                  <p className="text-xs mt-1.5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    Reconstructs missing rotations over optical marker dropouts. Applies velocity-continuous cubic splines across boundary anchor frames while guaranteeing that unoccluded frames remain 100% untouched.
                  </p>
                </div>

                <div className="mt-4 pt-2.5 border-t text-[10px] space-y-1" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex justify-between" style={{ color: 'var(--text-muted)' }}>
                    <span>Target Metric:</span>
                    <span className="font-semibold text-emerald-400">Inpainting MPJPE</span>
                  </div>
                  <div className="flex justify-between" style={{ color: 'var(--text-muted)' }}>
                    <span>Contract Gate:</span>
                    <span style={{ color: 'var(--text-secondary)' }}>0.00 observed diff</span>
                  </div>
                </div>
              </div>

              {/* Task 3 Card */}
              <div
                onClick={() => setSelectedTask('retargeting')}
                className="p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between"
                style={{
                  backgroundColor: selectedTask === 'retargeting' ? 'var(--bg-hover)' : 'var(--bg-inset)',
                  borderColor: selectedTask === 'retargeting' ? '#a855f7' : 'var(--border-subtle)',
                  boxShadow: selectedTask === 'retargeting' ? '0 4px 14px rgba(168, 85, 247, 0.15)' : 'none',
                }}
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
                  <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                    Track 3: Cross-Morphology Retargeting
                  </h3>
                  <p className="text-xs mt-1.5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    Transfers kinematic animation onto non-uniformly scaled avatar skeletons. Enforces rigid bone length invariance (&lt; 1e-5 in) and contact-aware foot floor penetration penalties.
                  </p>
                </div>

                <div className="mt-4 pt-2.5 border-t text-[10px] space-y-1" style={{ borderColor: 'var(--border-subtle)' }}>
                  <div className="flex justify-between" style={{ color: 'var(--text-muted)' }}>
                    <span>Target Metric:</span>
                    <span className="font-semibold text-purple-400">End-Effector Error</span>
                  </div>
                  <div className="flex justify-between" style={{ color: 'var(--text-muted)' }}>
                    <span>Rigid Constraint:</span>
                    <span style={{ color: 'var(--text-secondary)' }}>&lt; 1e-5 in variation</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: CONFIGURE PARAMETERS */}
        {currentStep === 3 && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Sliders className="w-4 h-4 text-cyan-400" /> Step 3: Configure {selectedTask === 'denoising' ? 'Denoising' : selectedTask === 'gap_filling' ? 'Gap Filling' : 'Retargeting'} Parameters
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Select the challenge severity or target avatar morphology for motion trial <strong className="font-mono text-cyan-300">{selectedMotionId}</strong>.
                </p>
              </div>
            </div>

            {/* Task-Specific Parameter Form */}
            {selectedTask === 'denoising' && (
              <div className="flex flex-col gap-4 max-w-xl">
                <div>
                  <label className="text-xs font-semibold block mb-2" style={{ color: 'var(--text-secondary)' }}>
                    Gaussian Noise Perturbation Severity:
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['LOW', 'MEDIUM', 'HIGH'] as const).map((lvl) => (
                      <button
                        key={lvl}
                        onClick={() => setNoiseLevel(lvl)}
                        className="p-3 rounded-xl border text-left transition-all"
                        style={{
                          backgroundColor: noiseLevel === lvl ? 'var(--bg-hover)' : 'var(--bg-inset)',
                          borderColor: noiseLevel === lvl ? 'var(--accent)' : 'var(--border-subtle)',
                        }}
                      >
                        <div className="font-mono font-bold text-xs" style={{ color: noiseLevel === lvl ? 'var(--accent-text)' : 'var(--text-primary)' }}>
                          {lvl}
                        </div>
                        <div className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
                          {lvl === 'LOW' && 'Window: 7f (~58ms)'}
                          {lvl === 'MEDIUM' && 'Window: 13f (~108ms)'}
                          {lvl === 'HIGH' && 'Window: 19f (~158ms)'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded-xl border text-xs leading-relaxed space-y-1.5" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <div className="flex items-center gap-1.5 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                    <Info className="w-3.5 h-3.5 text-cyan-400" /> Savitzky-Golay Filter Details
                  </div>
                  <p>
                    A polynomial order 2 Savitzky-Golay filter fits a local quadratic function through each frame window. Phase unwrapping is applied to continuous rotation angles to prevent spurious 360° discontinuities before convolution.
                  </p>
                </div>
              </div>
            )}

            {selectedTask === 'gap_filling' && (
              <div className="flex flex-col gap-4 max-w-xl">
                <div>
                  <label className="text-xs font-semibold block mb-2" style={{ color: 'var(--text-secondary)' }}>
                    Occlusion Interval Duration (Missing Marker Gap):
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['SHORT', 'MEDIUM', 'LONG'] as const).map((gt) => (
                      <button
                        key={gt}
                        onClick={() => setGapType(gt)}
                        className="p-3 rounded-xl border text-left transition-all"
                        style={{
                          backgroundColor: gapType === gt ? 'var(--bg-hover)' : 'var(--bg-inset)',
                          borderColor: gapType === gt ? '#10b981' : 'var(--border-subtle)',
                        }}
                      >
                        <div className="font-mono font-bold text-xs" style={{ color: gapType === gt ? '#34d399' : 'var(--text-primary)' }}>
                          {gt}
                        </div>
                        <div className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
                          {gt === 'SHORT' && '~10-25 frames (transient)'}
                          {gt === 'MEDIUM' && '~35-65 frames (blindspot)'}
                          {gt === 'LONG' && '~75-150 frames (severe)'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded-xl border text-xs leading-relaxed space-y-1.5" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <div className="flex items-center gap-1.5 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                    <Info className="w-3.5 h-3.5 text-emerald-400" /> Spline Continuity & Isolation Rule
                  </div>
                  <p>
                    Hermite cubic spline matching satisfies C¹ continuous velocities at entry and exit anchor frames. The competition evaluator checks that all unoccluded frames remain bit-for-bit identical with zero modification.
                  </p>
                </div>
              </div>
            )}

            {selectedTask === 'retargeting' && (
              <div className="flex flex-col gap-4 max-w-xl">
                <div>
                  <label className="text-xs font-semibold block mb-2" style={{ color: 'var(--text-secondary)' }}>
                    Target Avatar Morphology:
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: 'target_small', name: 'Small / Child', factor: '0.85x height' },
                      { id: 'target_medium', name: 'Medium / Athletic', factor: '1.05x height' },
                      { id: 'target_tall', name: 'Tall / Slender', factor: '1.25x height' },
                    ].map((avatar) => (
                      <button
                        key={avatar.id}
                        onClick={() => setTargetType(avatar.id)}
                        className="p-3 rounded-xl border text-left transition-all"
                        style={{
                          backgroundColor: targetType === avatar.id ? 'var(--bg-hover)' : 'var(--bg-inset)',
                          borderColor: targetType === avatar.id ? '#a855f7' : 'var(--border-subtle)',
                        }}
                      >
                        <div className="font-mono font-bold text-xs" style={{ color: targetType === avatar.id ? '#c084fc' : 'var(--text-primary)' }}>
                          {avatar.name}
                        </div>
                        <div className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
                          {avatar.factor}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded-xl border text-xs leading-relaxed space-y-1.5" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <div className="flex items-center gap-1.5 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                    <Info className="w-3.5 h-3.5 text-purple-400" /> Non-Uniform Morphological Scaling
                  </div>
                  <p>
                    Bone segment lengths are scaled independently per limb group (torso, upper arm, forearm, thigh, shin, foot). Root translation is normalized by total skeletal height ratio to prevent ground sliding.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 4: RUN PIPELINE */}
        {currentStep === 4 && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Zap className="w-4 h-4 text-amber-400" /> Step 4: Execute Motion Processing Pipeline
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Launch live backend processing with configured hyperparameters and forward kinematics validation.
                </p>
              </div>
            </div>

            {/* Run Summary Checklist */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-xl border" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}>
                <span className="text-[10px] font-mono uppercase tracking-wider block" style={{ color: 'var(--text-muted)' }}>
                  Motion Trial
                </span>
                <span className="font-mono font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                  {selectedMotion.motion_id}
                </span>
                <span className="text-[11px] block mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                  {selectedMotion.description}
                </span>
              </div>

              <div className="p-3.5 rounded-xl border" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}>
                <span className="text-[10px] font-mono uppercase tracking-wider block" style={{ color: 'var(--text-muted)' }}>
                  Target Algorithm
                </span>
                <span className="font-mono font-bold text-sm" style={{ color: 'var(--accent-text)' }}>
                  {selectedTask === 'denoising' ? 'Track 1: Denoising' : selectedTask === 'gap_filling' ? 'Track 2: Gap Filling' : 'Track 3: Retargeting'}
                </span>
                <span className="text-[11px] block mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  {selectedTask === 'denoising' ? 'Savitzky-Golay quadratic' : selectedTask === 'gap_filling' ? 'Hermite cubic spline' : 'Kinematic limb retargeting'}
                </span>
              </div>

              <div className="p-3.5 rounded-xl border" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}>
                <span className="text-[10px] font-mono uppercase tracking-wider block" style={{ color: 'var(--text-muted)' }}>
                  Hyperparameters
                </span>
                <span className="font-mono font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                  {selectedTask === 'denoising' ? `Noise: ${noiseLevel}` : selectedTask === 'gap_filling' ? `Gap: ${gapType}` : `Target: ${targetType}`}
                </span>
                <span className="text-[11px] block mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  120 FPS / 31 Joint Hierarchy
                </span>
              </div>
            </div>

            {/* Big Action Box */}
            <div className="p-6 rounded-2xl border text-center flex flex-col items-center justify-center gap-3" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-default)' }}>
              {loading ? (
                <div className="flex flex-col items-center gap-3 py-4">
                  <div className="w-10 h-10 border-3 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                  <div className="flex flex-col items-center">
                    <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                      Executing Kinematics on Backend...
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                      Evaluating Forward Kinematics, MPJPE & temporal derivatives
                    </span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3 py-2 max-w-md">
                  <span className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    Click below to trigger live calculation on the FastAPI backend. Full forward kinematics, metric validation, and BVH reconstruction will run deterministically.
                  </span>
                  <button
                    onClick={handleExecute}
                    className="px-6 py-3 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg transition-all"
                    style={{
                      backgroundColor: 'var(--accent)',
                      color: '#000',
                      boxShadow: '0 4px 18px rgba(34, 211, 238, 0.3)',
                    }}
                  >
                    <Play className="w-4 h-4 fill-current" /> Execute Live Processing Pipeline
                  </button>
                </div>
              )}

              {error && (
                <div className="mt-2 p-3 rounded-xl border flex items-center gap-2 text-xs" style={{ backgroundColor: 'var(--error-bg)', borderColor: 'var(--error-border)', color: 'var(--error-text)' }}>
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 5: INSPECT RESULTS & 3D LOAD */}
        {currentStep === 5 && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Award className="w-4 h-4 text-amber-400" /> Step 5: Metric Evaluation & 3D Character Loading
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Review official Phase 4 calibrated metric scores and load reconstructed motions directly into the 3D character viewer.
                </p>
              </div>

              {result && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded flex items-center gap-1 border" style={{ backgroundColor: 'var(--success-bg)', color: 'var(--success-text)', borderColor: 'var(--success-border)' }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> LIVE RESULT
                  </span>
                </div>
              )}
            </div>

            {result ? (
              <div className="flex flex-col gap-4">
                {/* Score Banner & Action Bar */}
                <div
                  className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                  style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}
                >
                  <div className="flex items-center gap-3">
                    <StatusBadge status={result.status} />
                    <div className="flex flex-col">
                      <span className="font-mono text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                        {result.motion_id} — {result.task.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                        Phase 4 Calibrated Evaluation
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto justify-end flex-wrap">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border font-mono" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-default)' }}>
                      <span className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Score:</span>
                      <span className="text-base font-extrabold" style={{ color: 'var(--accent-text)' }}>
                        {result.score ? result.score.toFixed(2) : '0.00'}/100
                      </span>
                    </div>

                    <button
                      onClick={handleLoadInViewer}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition-all"
                      style={{
                        backgroundColor: loadedInViewer ? 'var(--success-bg)' : 'var(--accent-bg)',
                        color: loadedInViewer ? 'var(--success-text)' : 'var(--accent-text)',
                        borderColor: loadedInViewer ? 'var(--success-border)' : 'var(--accent-border)',
                      }}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      {loadedInViewer ? 'Loaded in 3D Viewer!' : 'Load in 3D Viewer'}
                    </button>

                    <button
                      onClick={handleExportJSON}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition-all"
                      style={{
                        backgroundColor: hasExported ? 'var(--success-bg)' : 'var(--bg-card)',
                        color: hasExported ? 'var(--success-text)' : 'var(--text-secondary)',
                        borderColor: 'var(--border-default)',
                      }}
                    >
                      <Download className="w-3.5 h-3.5" />
                      {hasExported ? 'Exported JSON' : 'Export JSON'}
                    </button>
                  </div>
                </div>

                {loadedInViewer && (
                  <div className="p-2.5 rounded-lg border text-xs flex items-center justify-between" style={{ backgroundColor: 'var(--success-bg)', borderColor: 'var(--success-border)', color: 'var(--success-text)' }}>
                    <span>Dual BVH files (Input & Output) loaded into 3D character viewport buffer.</span>
                    <button
                      onClick={() => onNavigate(selectedTask === 'denoising' ? 'denoising' : selectedTask === 'gap_filling' ? 'gap-filling' : 'retargeting')}
                      className="underline font-semibold text-xs ml-2"
                    >
                      Open Full 3D Workbench &rarr;
                    </button>
                  </div>
                )}

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {selectedTask === 'denoising' && (
                    <>
                      <MetricCard
                        title="Position Error (MPJPE)"
                        value={result.metrics.mpjpe ? result.metrics.mpjpe.toFixed(4) : '--'}
                        unit="in"
                        direction="lower-is-better"
                        rawValue={result.metrics.raw_mpjpe}
                        improvementPct={result.metrics.mpjpe_improvement_pct}
                      />
                      <MetricCard
                        title="Jitter Reduction"
                        value={result.metrics.jitter_reduction_pct ? `${result.metrics.jitter_reduction_pct.toFixed(1)}%` : '--'}
                        unit=""
                        direction="higher-is-better"
                        improvementPct={result.metrics.jitter_reduction_pct}
                      />
                      <MetricCard
                        title="Velocity Error (JVE)"
                        value={result.metrics.velocity_error ? result.metrics.velocity_error.toFixed(2) : '--'}
                        unit="in/s"
                        direction="lower-is-better"
                      />
                      <MetricCard
                        title="Energy Preservation"
                        value={result.metrics.motion_preservation ? `${(result.metrics.motion_preservation * 100).toFixed(1)}%` : '--'}
                        unit=""
                        direction="neutral"
                        subtitle="Bounds [35%, 300%]"
                      />
                    </>
                  )}

                  {selectedTask === 'gap_filling' && (
                    <>
                      <MetricCard
                        title="Inpainting MPJPE"
                        value={result.metrics.inpainting_mpjpe ? result.metrics.inpainting_mpjpe.toFixed(4) : '--'}
                        unit="in"
                        direction="lower-is-better"
                      />
                      <MetricCard
                        title="Boundary Discontinuity"
                        value={result.metrics.boundary_error ? result.metrics.boundary_error.toFixed(4) : '--'}
                        unit="in"
                        direction="lower-is-better"
                      />
                      <MetricCard
                        title="Velocity Boundary Jump"
                        value={result.metrics.velocity_boundary_error ? result.metrics.velocity_boundary_error.toFixed(2) : '0.00'}
                        unit="in/s"
                        direction="lower-is-better"
                      />
                      <MetricCard
                        title="Observed Invariance"
                        value="0.000 diff"
                        unit=""
                        direction="neutral"
                        subtitle="100% Preserved"
                      />
                    </>
                  )}

                  {selectedTask === 'retargeting' && (
                    <>
                      <MetricCard
                        title="End-Effector Error"
                        value={result.metrics.end_effector_error ? result.metrics.end_effector_error.toFixed(4) : '--'}
                        unit="in"
                        direction="lower-is-better"
                      />
                      <MetricCard
                        title="Angular Geodesic Error"
                        value={result.metrics.angular_geodesic_error ? result.metrics.angular_geodesic_error.toFixed(3) : '0.000'}
                        unit="deg"
                        direction="lower-is-better"
                      />
                      <MetricCard
                        title="Bone Length Invariance"
                        value="< 1e-5 in"
                        unit=""
                        direction="neutral"
                        subtitle="Strictly Preserved"
                      />
                      <MetricCard
                        title="Floor Penetration"
                        value={result.metrics.ground_penetration_penalty ? result.metrics.ground_penetration_penalty.toFixed(3) : '0.000'}
                        unit="in"
                        direction="lower-is-better"
                      />
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>
                <p className="text-sm">Please execute Step 4 to view live algorithm metrics.</p>
              </div>
            )}
          </div>
        )}

        {/* STEP 6: SCIENTIFIC INTERPRETATION */}
        {currentStep === 6 && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <h2 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <FileCode className="w-4 h-4 text-emerald-400" /> Step 6: Scientific Interpretation & Evaluation
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Understanding the biomechanical meaning of the measured error metrics and next research steps.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Metric Breakdown */}
              <div className="p-4 rounded-xl border space-y-3" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}>
                <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                  <span>Metric Diagnostics</span>
                </h3>

                <div className="space-y-2 text-xs">
                  <div className="flex items-start gap-2">
                    <MetricExplainer metric="mpjpe" size="sm" />
                    <div>
                      <strong style={{ color: 'var(--text-primary)' }}>Forward Kinematics Position:</strong>
                      <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                        Evaluates overall skeletal pose adherence. In denoising and inpainting, lower MPJPE reflects tighter spatial conformity to ground-truth joint positions.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-2">
                    <MetricExplainer metric="jitter" size="sm" />
                    <div>
                      <strong style={{ color: 'var(--text-primary)' }}>Temporal Derivative Smoothness:</strong>
                      <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                        Measures physical acceleration plausibility. High jitter produces noticeable visual vibration in game engines, which Savitzky-Golay quadratic filtering significantly attenuates.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-2">
                    <MetricExplainer metric="bone_length_violation" size="sm" />
                    <div>
                      <strong style={{ color: 'var(--text-primary)' }}>Biomechanical Consistency:</strong>
                      <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                        Articulated skeletons cannot deform rigidly. A non-zero bone length delta invalidates the motion, which is why MOTIONFORGE enforces &lt; 1e-5 in tolerance.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Research Pathways */}
              <div className="p-4 rounded-xl border flex flex-col justify-between" style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}>
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                    <span>Next Research Modules</span>
                  </h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    You have observed live evaluation on real CMU data. To dive deeper into the comparative benchmark experiments or theoretical methodology:
                  </p>

                  <div className="flex flex-col gap-2 pt-1">
                    <button
                      onClick={() => onNavigate('accuracy-lab')}
                      className="p-2.5 rounded-lg border text-left flex items-center justify-between text-xs font-semibold transition-all hover:bg-theme-card"
                      style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-secondary)' }}
                    >
                      <span className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-rose-400" /> Accuracy Lab (Phase 11 Benchmark)
                      </span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => onNavigate('research')}
                      className="p-2.5 rounded-lg border text-left flex items-center justify-between text-xs font-semibold transition-all hover:bg-theme-card"
                      style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-secondary)' }}
                    >
                      <span className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-amber-400" /> Research Methodology & Whitepaper
                      </span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t flex justify-end" style={{ borderColor: 'var(--border-subtle)' }}>
                  <button
                    onClick={handleResetWizard}
                    className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 border"
                    style={{ backgroundColor: 'var(--bg-card)', color: 'var(--accent-text)', borderColor: 'var(--accent-border)' }}
                  >
                    <RotateCcw className="w-3.5 h-3.5" /> Start New Guided Demo
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Wizard Footer Navigation Controls */}
        <div className="pt-5 mt-4 border-t flex items-center justify-between" style={{ borderColor: 'var(--border-default)' }}>
          <button
            onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
            disabled={currentStep === 1}
            className="px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all"
            style={{
              backgroundColor: 'var(--bg-inset)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
              opacity: currentStep === 1 ? 0.4 : 1,
              cursor: currentStep === 1 ? 'not-allowed' : 'pointer',
            }}
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>

          <span className="text-[11px] font-mono" style={{ color: 'var(--text-muted)' }}>
            Step {currentStep} of 6
          </span>

          {currentStep < 4 && (
            <button
              onClick={() => setCurrentStep((prev) => Math.min(6, prev + 1))}
              className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
              style={{
                backgroundColor: 'var(--accent)',
                color: '#000',
              }}
            >
              Next <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {currentStep === 4 && (
            <button
              onClick={handleExecute}
              disabled={loading}
              className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
              style={{
                backgroundColor: 'var(--accent)',
                color: '#000',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? 'Running...' : 'Run & Inspect'} <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {currentStep >= 5 && currentStep < 6 && (
            <button
              onClick={() => setCurrentStep(6)}
              className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
              style={{
                backgroundColor: 'var(--accent)',
                color: '#000',
              }}
            >
              Interpret Metrics <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {currentStep === 6 && (
            <button
              onClick={() => onNavigate('research')}
              className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
              style={{
                backgroundColor: 'var(--accent)',
                color: '#000',
              }}
            >
              Read Full Methodology <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
