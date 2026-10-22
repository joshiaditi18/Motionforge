import { MotionItem, GapMetadataItem, TaskResult, RunnerConfig, RunnerResultSummary } from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export async function fetchHealth(): Promise<{ status: string; competition: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Backend health check failed');
  return res.json();
}

export async function fetchMotions(category?: string): Promise<MotionItem[]> {
  const url = category && category !== 'All' ? `${API_BASE}/motions?category=${encodeURIComponent(category)}` : `${API_BASE}/motions`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch motions');
  return res.json();
}

export async function fetchMotionDetail(motionId: string): Promise<MotionItem> {
  const res = await fetch(`${API_BASE}/motions/${motionId}`);
  if (!res.ok) throw new Error(`Failed to fetch motion ${motionId}`);
  return res.json();
}

export async function fetchMotionBVH(
  motionId: string,
  variant: 'clean' | 'denoising' | 'gap_filling' | 'retargeting' = 'clean',
  subvariant?: string
): Promise<string> {
  const params = new URLSearchParams({ variant });
  if (subvariant) params.append('subvariant', subvariant);
  const res = await fetch(`${API_BASE}/motions/${motionId}/bvh?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load BVH for ${motionId} (${variant})`);
  return res.text();
}

export async function fetchGapMetadata(): Promise<Record<string, GapMetadataItem>> {
  const res = await fetch(`${API_BASE}/tasks/gap_metadata`);
  if (!res.ok) throw new Error('Failed to fetch gap metadata');
  return res.json();
}

export async function runDenoising(motionId: string, noiseLevel: string = 'MEDIUM'): Promise<TaskResult> {
  const res = await fetch(`${API_BASE}/tasks/denoising`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ motion_id: motionId, noise_level: noiseLevel }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Denoising request failed' }));
    throw new Error(err.detail || 'Denoising execution error');
  }
  return res.json();
}

export async function runGapFilling(
  motionId: string,
  gapType: string = 'MEDIUM',
  customJoint?: string,
  customStart?: number,
  customEnd?: number,
  method: string = 'cubic'
): Promise<TaskResult> {
  const res = await fetch(`${API_BASE}/tasks/gap_filling`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      motion_id: motionId,
      gap_type: gapType,
      custom_joint: customJoint,
      custom_start: customStart,
      custom_end: customEnd,
      method: method,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Gap filling request failed' }));
    throw new Error(err.detail || 'Gap filling execution error');
  }
  return res.json();
}

export async function runRetargeting(motionId: string, targetType: string = 'target_medium'): Promise<TaskResult> {
  const res = await fetch(`${API_BASE}/tasks/retargeting`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ motion_id: motionId, target_type: targetType }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Retargeting request failed' }));
    throw new Error(err.detail || 'Retargeting execution error');
  }
  return res.json();
}

export async function fetchRunnerConfig(): Promise<RunnerConfig> {
  const res = await fetch(`${API_BASE}/runner/config`);
  if (!res.ok) throw new Error('Failed to fetch runner config');
  return res.json();
}

export async function fetchRunnerResults(): Promise<RunnerResultSummary[]> {
  const res = await fetch(`${API_BASE}/runner/results`);
  if (!res.ok) throw new Error('Failed to fetch runner results');
  return res.json();
}

export async function fetchRunnerResultDetail(filename: string): Promise<any> {
  const res = await fetch(`${API_BASE}/runner/results/${filename}`);
  if (!res.ok) throw new Error(`Failed to fetch result detail ${filename}`);
  return res.json();
}

export async function fetchAccuracyMethods(): Promise<Record<string, Array<{ id: string; name: string; category: string; description: string }>>> {
  const res = await fetch(`${API_BASE}/accuracy/methods`);
  if (!res.ok) throw new Error('Failed to fetch accuracy methods');
  return res.json();
}

export async function compareAccuracy(payload: {
  task: string;
  motion_id: string;
  method_baseline?: string;
  method_experimental?: string;
  noise_level?: string;
  gap_type?: string;
  target_type?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/accuracy/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Comparison request failed' }));
    throw new Error(err.detail || 'Accuracy comparison error');
  }
  return res.json();
}

export async function fetchAccuracyBenchmarks(): Promise<any> {
  const res = await fetch(`${API_BASE}/accuracy/benchmarks`);
  if (!res.ok) throw new Error('Failed to fetch benchmark results');
  return res.json();
}

// ─── Demo API ────────────────────────────────────────────────────────────────

export async function fetchDemoTaskDescriptions(): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/tasks`);
  if (!res.ok) throw new Error('Failed to fetch demo task descriptions');
  return res.json();
}

export async function fetchDemoGlossary(): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/glossary`);
  if (!res.ok) throw new Error('Failed to fetch metric glossary');
  return res.json();
}

/** Download a JSON result as a file in the browser */
export function downloadResultAsJSON(result: any, filename: string = 'motionforge_result.json'): void {
  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(result, null, 2));
  const a = document.createElement('a');
  a.setAttribute('href', dataStr);
  a.setAttribute('download', filename);
  document.body.appendChild(a);
  a.click();
  a.remove();
}
