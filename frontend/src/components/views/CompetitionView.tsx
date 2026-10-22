import React, { useState, useEffect } from 'react';
import { RunnerConfig, RunnerResultSummary } from '../../types';
import { fetchRunnerConfig, fetchRunnerResults, fetchRunnerResultDetail } from '../../services/api';
import { Trophy, ShieldCheck, CheckCircle2, FileText, ChevronRight, RefreshCw, Download, Layers } from 'lucide-react';
import { StatusBadge } from '../ui/StatusBadge';

export const CompetitionView: React.FC = () => {
  const [config, setConfig] = useState<RunnerConfig | null>(null);
  const [results, setResults] = useState<RunnerResultSummary[]>([]);
  const [selectedResult, setSelectedResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cfg, res] = await Promise.all([fetchRunnerConfig(), fetchRunnerResults()]);
      setConfig(cfg);
      setResults(res);
      if (res.length > 0) {
        const detail = await fetchRunnerResultDetail(res[0].file);
        setSelectedResult(detail);
      }
    } catch (err) {
      console.error('Failed to load runner data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectResult = async (filename: string) => {
    try {
      const detail = await fetchRunnerResultDetail(filename);
      setSelectedResult(detail);
    } catch (err) {
      console.error('Failed to load result detail:', err);
    }
  };

  const handleExportJSON = () => {
    if (!selectedResult) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(selectedResult, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${selectedResult.job_id || 'result'}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto flex flex-col gap-5" style={{ color: 'var(--text-primary)' }}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3.5 border-b border-theme">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Trophy className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-bold text-theme-primary flex items-center gap-2">
              <span>Competition Evaluation & Audit Studio</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Phase 5/6 Pipeline
              </span>
            </h2>
            <p className="text-[11px] text-theme-muted">
              Deterministic Phase 5 gatekeeping audit logs, Phase 4 scoring breakdowns, and result artifacts
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="p-1.5 rounded-lg bg-theme-card border border-theme hover:border-slate-700 text-theme-secondary hover:text-theme-primary transition-colors flex items-center gap-1.5 text-xs font-medium"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Artifacts</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left Column: Official Rules & Artifacts List */}
        <div className="flex flex-col gap-4">
          {/* Official Scoring Weights Card */}
          <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col gap-3">
            <h3 className="text-xs font-bold text-theme-secondary uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" /> Frozen Competition Weights
            </h3>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex items-center justify-between bg-theme-inset p-2 rounded-lg border border-theme-sub">
                <span className="text-theme-secondary font-sans">Task 1: Denoising</span>
                <span className="font-bold text-cyan-400">30.0%</span>
              </div>
              <div className="flex items-center justify-between bg-theme-inset p-2 rounded-lg border border-theme-sub">
                <span className="text-theme-secondary font-sans">Task 2: Gap Filling</span>
                <span className="font-bold text-emerald-400">30.0%</span>
              </div>
              <div className="flex items-center justify-between bg-theme-inset p-2 rounded-lg border border-theme-sub">
                <span className="text-theme-secondary font-sans">Task 3: Retargeting</span>
                <span className="font-bold text-purple-400">40.0%</span>
              </div>
            </div>
            <p className="text-[10px] text-theme-muted leading-relaxed border-t border-theme pt-2">
              Composite score: S_overall = 0.30 &times; S_1 + 0.30 &times; S_2 + 0.40 &times; S_3. Normalization calibrated via exponential decay (&tau;).
            </p>
          </div>

          {/* Past Runner Execution Artifacts */}
          <div className="bg-theme-card border border-theme rounded-xl p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between pb-1 border-b border-theme">
              <h3 className="text-xs font-bold text-theme-secondary uppercase tracking-wider">
                Runner Execution Artifacts
              </h3>
              <span className="text-[10px] text-theme-muted font-mono">{results.length} total</span>
            </div>

            {results.length === 0 ? (
              <div className="text-xs text-theme-muted p-3 text-center bg-slate-950/50 rounded-lg border border-theme-sub">
                No past runner artifacts found in <code>runner_results/</code>.
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {results.map((r) => {
                  const isSelected = selectedResult?.job_id === r.job_id;
                  return (
                    <div
                      key={r.job_id}
                      onClick={() => handleSelectResult(r.file)}
                      className={`p-2.5 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                        isSelected
                          ? 'bg-slate-800 border-cyan-500/50 text-theme-primary shadow-sm'
                          : 'bg-theme-inset border-theme-sub text-theme-secondary hover:bg-theme-hover'
                      }`}
                    >
                      <div className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-cyan-400">
                            Job {r.job_id.slice(0, 8)}
                          </span>
                          <StatusBadge status={r.status} size="sm" />
                        </div>
                        <span className="text-[10px] text-theme-muted font-mono">
                          Validator: {r.validation_status || 'VALID'}
                        </span>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-theme-muted" />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Result Artifact Inspector */}
        <div className="lg:col-span-2 bg-theme-card border border-theme rounded-xl p-4 sm:p-5 flex flex-col gap-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-theme">
            <div>
              <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-theme-muted">
                Result Artifact Inspector
              </span>
              <h3 className="text-sm font-bold text-theme-primary font-mono">
                {selectedResult ? `Job ID: ${selectedResult.job_id}` : 'Select a runner artifact'}
              </h3>
            </div>

            {selectedResult && (
              <button
                onClick={handleExportJSON}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-theme-secondary hover:text-theme-primary border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <Download className="w-3.5 h-3.5" /> Export JSON
              </button>
            )}
          </div>

          {selectedResult ? (
            <div className="flex flex-col gap-3.5">
              {/* Summary KPIs */}
              <div className="grid grid-cols-3 gap-2.5">
                <div className="bg-theme-inset p-2.5 rounded-lg border border-theme-sub">
                  <span className="text-[10px] text-theme-muted uppercase font-mono">Job Status</span>
                  <div className="text-xs font-bold font-mono text-emerald-400 mt-0.5">
                    {selectedResult.job_status}
                  </div>
                </div>
                <div className="bg-theme-inset p-2.5 rounded-lg border border-theme-sub">
                  <span className="text-[10px] text-theme-muted uppercase font-mono">Validation</span>
                  <div className="text-xs font-bold font-mono text-cyan-400 mt-0.5">
                    {selectedResult.validation_status}
                  </div>
                </div>
                <div className="bg-theme-inset p-2.5 rounded-lg border border-theme-sub">
                  <span className="text-[10px] text-theme-muted uppercase font-mono">Overall Score</span>
                  <div className="text-xs font-bold font-mono text-amber-400 mt-0.5">
                    {selectedResult.overall_score !== null && selectedResult.overall_score !== undefined
                      ? `${selectedResult.overall_score.toFixed(2)} / 100`
                      : 'Completed'}
                  </div>
                </div>
              </div>

              {/* Formatted JSON Output */}
              <div>
                <label className="text-[11px] font-medium text-theme-muted block mb-1">
                  Structured Result Artifact:
                </label>
                <pre className="bg-theme-inset border border-theme-sub rounded-lg p-3 text-[11px] font-mono text-theme-secondary max-h-96 overflow-y-auto leading-relaxed select-text">
                  {JSON.stringify(selectedResult, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="text-xs text-theme-muted p-8 text-center flex flex-col items-center gap-2">
              <FileText className="w-8 h-8 text-slate-600" />
              <span>Select an artifact from the list to view its official evaluation breakdown.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
