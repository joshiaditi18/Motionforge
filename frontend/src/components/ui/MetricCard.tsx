import React from 'react';
import { Info, TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  title: React.ReactNode;
  value: string | number;
  unit?: string;
  rawValue?: string | number;
  improvementPct?: number;
  direction?: 'lower-is-better' | 'higher-is-better' | 'neutral';
  tooltip?: string;
  accent?: 'cyan' | 'emerald' | 'purple' | 'amber' | 'neutral';
  subtitle?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  rawValue,
  improvementPct,
  direction = 'lower-is-better',
  tooltip,
  accent = 'cyan',
  subtitle,
}) => {
  const isGood =
    improvementPct !== undefined
      ? improvementPct > 0
      : direction === 'lower-is-better';

  return (
    <div
      className="rounded-xl p-3.5 flex flex-col justify-between transition-all shadow-sm border"
      style={{
        backgroundColor: 'var(--bg-card)',
        borderColor: 'var(--border-default)',
      }}
    >
      <div>
        <div className="flex items-center justify-between gap-1 mb-1.5">
          <span
            className="text-[11px] font-medium tracking-wide flex items-center gap-1"
            style={{ color: 'var(--text-muted)' }}
          >
            {title}
            {tooltip && (
              <span className="relative group/tip cursor-help">
                <Info className="w-3 h-3 transition-colors" style={{ color: 'var(--text-faint)' }} />
                <span
                  className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 hidden group-hover/tip:block w-48 p-2 text-[10px] rounded-md shadow-xl border pointer-events-none z-30 leading-snug"
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    color: 'var(--text-secondary)',
                    borderColor: 'var(--border-strong)',
                  }}
                >
                  {tooltip}
                </span>
              </span>
            )}
          </span>

          {direction !== 'neutral' && (
            <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
              {direction === 'lower-is-better' ? '↓ lower is better' : '↑ higher is better'}
            </span>
          )}
        </div>

        <div className="flex items-baseline justify-between mt-1">
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono tracking-tight" style={{ color: 'var(--text-primary)' }}>
              {value}
            </span>
            {unit && <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{unit}</span>}
          </div>

          {improvementPct !== undefined && (
            <div
              className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded flex items-center gap-0.5 border"
              style={
                isGood
                  ? { backgroundColor: 'var(--success-bg)', color: 'var(--success-text)', borderColor: 'var(--success-border)' }
                  : { backgroundColor: 'var(--error-bg)', color: 'var(--error-text)', borderColor: 'var(--error-border)' }
              }
            >
              {isGood ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              <span>{improvementPct > 0 ? `+${improvementPct.toFixed(1)}%` : `${improvementPct.toFixed(1)}%`}</span>
            </div>
          )}
        </div>
      </div>

      {(rawValue !== undefined || subtitle) && (
        <div
          className="mt-2.5 pt-2 border-t flex items-center justify-between text-[10px] font-mono"
          style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}
        >
          {rawValue !== undefined && (
            <span>Raw Baseline: <strong className="font-normal">{rawValue} {unit}</strong></span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
