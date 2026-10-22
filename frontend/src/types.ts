export interface MotionItem {
  motion_id: string;
  description: string;
  category: string;
  fps: number;
  frame_count: number;
  duration_seconds: number;
  joint_count: number;
  root_joint: string;
  has_clean: boolean;
  available_tasks: {
    denoising: { LOW: boolean; MEDIUM: boolean; HIGH: boolean };
    gap_filling: { SHORT: boolean; MEDIUM: boolean; LONG: boolean };
    retargeting: { target_small: boolean; target_medium: boolean; target_tall: boolean };
  };
}

export interface GapMetadataItem {
  motion_id: string;
  gap_id: string;
  joint_name: string;
  start_frame: number;
  end_frame: number;
  gap_length: number;
  gap_type: string;
  output_file: string;
}

export interface TaskMetrics {
  // Denoising
  mpjpe?: number;
  velocity_error?: number;
  jitter?: number;
  motion_preservation?: number;
  raw_mpjpe?: number;
  raw_jitter?: number;
  mpjpe_improvement_pct?: number;
  jitter_reduction_pct?: number;

  // Gap filling
  inpainting_mpjpe?: number;
  boundary_error?: number;
  velocity_boundary_error?: number;
  foot_skating?: number;
  unmodified_max_diff?: number;
  target_joint?: string;
  distal_evaluated_joint?: string;
  gap_length_frames?: number;

  // Retargeting
  end_effector_error?: number;
  angular_geodesic_error?: number;
  bone_length_violation_max?: number;
  ground_penetration_penalty?: number;
  min_foot_height_y?: number;
  temporal_velocity_ratio?: number;
  target_avatar?: string;
}

export interface TaskResult {
  task: 'denoising' | 'gap_filling' | 'retargeting';
  motion_id: string;
  score: number;
  task_score: number;
  status: string;
  metrics: TaskMetrics;
  detail?: any;
  input_bvh: string;
  processed_bvh: string;
  noise_level?: string;
  gap_type?: string;
  gap_info?: {
    joint_name: string;
    start_frame: number;
    end_frame: number;
    length: number;
    method: string;
  };
  target_type?: string;
  target_config?: Record<string, number>;
}

export interface RunnerConfig {
  competition_name: string;
  contract_version: string;
  scoring_weights: {
    denoising: number;
    gap_filling: number;
    retargeting: number;
  };
  timeout_seconds: number;
  max_archive_size_mb: number;
}

export interface RunnerResultSummary {
  file: string;
  timestamp?: string;
  job_id: string;
  submission_id?: string;
  status: string;
  overall_score?: number | null;
  validation_status?: string;
}

export interface AccuracyMethod {
  id: string;
  name: string;
  category: 'baseline' | 'experimental';
  description: string;
}

export interface AccuracyComparisonResult {
  task: 'denoising' | 'gap_filling' | 'retargeting';
  motion_id: string;
  config: Record<string, any>;
  method_baseline: string;
  method_experimental: string;
  score_baseline: number;
  score_experimental: number;
  score_delta: number;
  runtime_baseline_ms: number;
  runtime_experimental_ms: number;
  metrics_baseline: Record<string, number>;
  metrics_experimental: Record<string, number>;
  error_curve: Array<{ frame: number; baseline_error: number; experimental_error: number }>;
  diagnostics: Record<string, any>;
  input_bvh: string;
  baseline_bvh: string;
  experimental_bvh: string;
}

export type ActiveTab = 'overview' | 'motion-lab' | 'denoising' | 'gap-filling' | 'retargeting' | 'accuracy-lab' | 'competition' | 'demo' | 'research';
export type ViewMode = 'single' | 'side-by-side' | 'overlay';
export type CameraPreset = 'perspective' | 'front' | 'side' | 'top';
