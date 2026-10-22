import React, { useState, useRef, useEffect } from 'react';
import { HelpCircle, Info, ArrowDown, ArrowUp, Minus } from 'lucide-react';

export type ExplainableMetric =
  | 'mpjpe'
  | 'jitter'
  | 'inpainting_error'
  | 'boundary_error'
  | 'end_effector_error'
  | 'bone_length_violation'
  | 'noise_level'
  | 'gap_type';

interface MetricMeta {
  title: string;
  unit: string;
  direction: 'lower-is-better' | 'higher-is-better' | 'zero-is-ideal' | 'informative';
  explanation: string;
  category: string;
}

const METRIC_DICTIONARY: Record<ExplainableMetric, MetricMeta> = {
  mpjpe: {
    title: 'Mean Per-Joint Position Error (MPJPE)',
    unit: 'inches (in)',
    direction: 'lower-is-better',
    category: 'Positional Accuracy',
    explanation:
      'Calculates Euclidean distance between joint positions computed via Forward Kinematics (FK) against ground truth across all 31 joints. Lower values represent higher geometric fidelity.',
  },
  jitter: {
    title: 'Acceleration Jitter Error',
    unit: 'in/s² (inches/sec²)',
    direction: 'lower-is-better',
    category: 'Temporal Smoothness',
    explanation:
      'Measures high-frequency second-order temporal finite difference acceleration. Minimizing jitter removes sensor noise and unnatural trembling while keeping authentic body dynamics.',
  },
  inpainting_error: {
    title: 'Inpainting Error (Gap MPJPE)',
    unit: 'inches (in)',
    direction: 'lower-is-better',
    category: 'Trajectory Recovery',
    explanation:
      'Mean position error specifically computed within the missing marker interval. Evaluates the algorithm’s ability to hallucinate plausible kinematic motion when optical line-of-sight is lost.',
  },
  boundary_error: {
    title: 'Boundary Discontinuity Jump',
    unit: 'inches (in) & in/s',
    direction: 'lower-is-better',
    category: 'Continuity & Spline Stitching',
    explanation:
      'Displacement and velocity step jumps at the entry and exit boundary frames of an occlusion gap. Smooth C¹ velocity matching eliminates visible jerk at reconnection points.',
  },
  end_effector_error: {
    title: 'End-Effector Spatial Error',
    unit: 'inches (in)',
    direction: 'lower-is-better',
    category: 'Distal Extremities',
    explanation:
      'Normalized Euclidean error of the 5 distal end effectors: Head, Left Hand, Right Hand, Left Foot, Right Foot. Crucial for ground contact, foot-skating avoidance, and hand manipulation.',
  },
  bone_length_violation: {
    title: 'Bone Length Invariance',
    unit: 'inches (in)',
    direction: 'zero-is-ideal',
    category: 'Biomechanical Rigidity',
    explanation:
      'Validates that articulated skeletal segments do not stretch or compress across frames. Rigid-body kinematics requires variance strictly < 1e-5 in.',
  },
  noise_level: {
    title: 'Gaussian Noise Severity',
    unit: 'LOW | MEDIUM | HIGH',
    direction: 'informative',
    category: 'Sensor Perturbation',
    explanation:
      'Severity of zero-mean Gaussian perturbation injected into Euler angles (LOW: 7f filter window, MEDIUM: 13f window, HIGH: 19f window) to simulate real-world optical capture errors.',
  },
  gap_type: {
    title: 'Occlusion Gap Severity',
    unit: 'SHORT | MEDIUM | LONG',
    direction: 'informative',
    category: 'Occlusion Duration',
    explanation:
      'Missing marker duration (SHORT: ~10-25 frames / ~150ms, MEDIUM: ~35-65 frames / ~400ms, LONG: ~75-150 frames / ~800ms) representing temporary camera blindspots and sensor dropouts.',
  },
};

export interface MetricExplainerProps {
  metric: ExplainableMetric | string;
  className?: string;
  size?: 'xs' | 'sm' | 'md';
}

export const MetricExplainer: React.FC<MetricExplainerProps> = ({
  metric,
  className = '',
  size = 'xs',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);

  // Normalize key
  const normalizedKey = metric
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '_') as ExplainableMetric;

  const data: MetricMeta = METRIC_DICTIONARY[normalizedKey] || {
    title: metric.replace(/_/g, ' '),
    unit: '--',
    direction: 'informative',
    category: 'Kinematic Metric',
    explanation: `Scientific metric evaluating motion capture quality for ${metric}.`,
  };

  // Close on outside click if opened via click
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutside);
    }
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [isOpen]);

  const iconSizes = {
    xs: 'w-3 h-3',
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
  };

  return (
    <span
      ref={containerRef}
      className={`relative inline-flex items-center align-middle ${className}`}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={`Explain metric ${data.title}`}
        className="cursor-help p-0.5 rounded transition-colors inline-flex items-center text-theme-muted hover:text-theme-accent focus:outline-none"
        style={{ color: 'var(--text-muted)' }}
      >
        <HelpCircle className={iconSizes[size]} />
      </button>

      {isOpen && (
        <div
          role="tooltip"
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 sm:w-72 p-3 rounded-xl shadow-2xl text-left border text-xs pointer-events-auto backdrop-blur-md animate-in fade-in zoom-in-95 duration-150"
          style={{
            backgroundColor: 'var(--bg-card)',
            borderColor: 'var(--border-strong)',
            color: 'var(--text-primary)',
            boxShadow: '0 12px 30px -4px rgba(0, 0, 0, 0.45)',
          }}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-1 pb-1.5 border-b" style={{ borderColor: 'var(--border-subtle)' }}>
            <div>
              <span className="text-[9px] uppercase tracking-wider font-mono font-bold block" style={{ color: 'var(--accent-text)' }}>
                {data.category}
              </span>
              <h4 className="text-xs font-bold leading-tight mt-0.5" style={{ color: 'var(--text-primary)' }}>
                {data.title}
              </h4>
            </div>
            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color: 'var(--accent-text)' }} />
          </div>

          {/* Unit & Direction Badge */}
          <div className="flex items-center justify-between gap-2 py-1.5 text-[10px] font-mono">
            <span style={{ color: 'var(--text-muted)' }}>
              Unit: <strong style={{ color: 'var(--text-secondary)' }}>{data.unit}</strong>
            </span>

            {data.direction === 'lower-is-better' && (
              <span
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-semibold text-[9px]"
                style={{ backgroundColor: 'var(--success-bg)', color: 'var(--success-text)', border: '1px solid var(--success-border)' }}
              >
                <ArrowDown className="w-2.5 h-2.5" /> Lower is better
              </span>
            )}
            {data.direction === 'higher-is-better' && (
              <span
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-semibold text-[9px]"
                style={{ backgroundColor: 'var(--success-bg)', color: 'var(--success-text)', border: '1px solid var(--success-border)' }}
              >
                <ArrowUp className="w-2.5 h-2.5" /> Higher is better
              </span>
            )}
            {data.direction === 'zero-is-ideal' && (
              <span
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-semibold text-[9px]"
                style={{ backgroundColor: 'var(--warning-bg)', color: 'var(--warning-text)', border: '1px solid var(--warning-border)' }}
              >
                <Minus className="w-2.5 h-2.5" /> Exact Zero Ideal
              </span>
            )}
            {data.direction === 'informative' && (
              <span
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-semibold text-[9px]"
                style={{ backgroundColor: 'var(--bg-inset)', color: 'var(--text-muted)', border: '1px solid var(--border-default)' }}
              >
                Informative
              </span>
            )}
          </div>

          {/* Plain-English Explanation */}
          <p className="text-[11px] leading-relaxed pt-1" style={{ color: 'var(--text-secondary)' }}>
            {data.explanation}
          </p>

          {/* Pointer caret arrow */}
          <div
            className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 border-b border-r"
            style={{
              backgroundColor: 'var(--bg-card)',
              borderColor: 'var(--border-strong)',
            }}
          />
        </div>
      )}
    </span>
  );
};
