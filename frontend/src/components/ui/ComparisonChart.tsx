import React from 'react';

interface ComparisonBarProps {
  label: string;
  rawValue: number;
  processedValue: number;
  unit: string;
  lowerIsBetter?: boolean;
}

export const ComparisonChart: React.FC<{
  title: string;
  subtitle?: string;
  items: ComparisonBarProps[];
}> = ({ title, subtitle, items }) => {
  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-3 border"
      style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
    >
      <div
        className="flex items-center justify-between pb-2 border-b"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div>
          <h4 className="text-xs font-bold tracking-wide" style={{ color: 'var(--text-secondary)' }}>{title}</h4>
          {subtitle && <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>}
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500/70" />
            <span style={{ color: 'var(--text-muted)' }}>Raw Input</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400" />
            <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Processed</span>
          </div>
        </div>
      </div>

      <div className="space-y-3 pt-1">
        {items.map((item, idx) => {
          const maxVal = Math.max(item.rawValue, item.processedValue, 1e-4);
          const rawPct = (item.rawValue / maxVal) * 100;
          const procPct = (item.processedValue / maxVal) * 100;
          const deltaPct = ((item.rawValue - item.processedValue) / Math.max(1e-4, item.rawValue)) * 100;

          return (
            <div key={idx} className="flex flex-col gap-1 text-xs">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                <span className="font-mono font-semibold" style={{ color: 'var(--accent-text)' }}>
                  {deltaPct > 0 ? `-${deltaPct.toFixed(1)}% Error` : `+${Math.abs(deltaPct).toFixed(1)}%`}
                </span>
              </div>

              {/* Stacked comparison bars */}
              <div className="space-y-1">
                {/* Raw Bar */}
                <div className="flex items-center gap-2">
                  <span className="w-16 text-[10px] font-mono text-right" style={{ color: 'var(--text-muted)' }}>Raw</span>
                  <div
                    className="flex-1 rounded h-3 overflow-hidden p-0.5 border"
                    style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}
                  >
                    <div
                      className="bg-rose-500/70 h-full rounded-sm transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(2, rawPct))}%` }}
                    />
                  </div>
                  <span className="w-20 text-[10px] text-rose-400 font-mono text-right">
                    {item.rawValue.toFixed(3)} {item.unit}
                  </span>
                </div>

                {/* Processed Bar */}
                <div className="flex items-center gap-2">
                  <span className="w-16 text-[10px] font-mono text-right font-medium" style={{ color: 'var(--accent-text)' }}>Output</span>
                  <div
                    className="flex-1 rounded h-3 overflow-hidden p-0.5 border"
                    style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-subtle)' }}
                  >
                    <div
                      className="bg-cyan-400 h-full rounded-sm shadow-sm shadow-cyan-400/50 transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(2, procPct))}%` }}
                    />
                  </div>
                  <span className="w-20 text-[10px] text-cyan-400 font-mono text-right font-semibold">
                    {item.processedValue.toFixed(3)} {item.unit}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
