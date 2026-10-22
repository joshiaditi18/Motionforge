import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface StatusBadgeProps {
  status: 'VALID' | 'REJECTED' | 'ERROR' | 'COMPLETED' | 'RUNNING' | 'PENDING' | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const s = status.toUpperCase();

  const configs: Record<string, { bg: string; text: string; border: string; icon: React.ReactNode }> = {
    VALID: {
      bg: 'bg-emerald-500/15',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    COMPLETED: {
      bg: 'bg-emerald-500/15',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    REJECTED: {
      bg: 'bg-rose-500/15',
      text: 'text-rose-400',
      border: 'border-rose-500/30',
      icon: <XCircle className="w-3 h-3" />,
    },
    ERROR: {
      bg: 'bg-amber-500/15',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
    RUNNING: {
      bg: 'bg-cyan-500/15',
      text: 'text-cyan-400',
      border: 'border-cyan-500/30',
      icon: <Clock className="w-3 h-3 animate-spin" />,
    },
    PENDING: {
      bg: 'bg-slate-800',
      text: 'text-slate-400',
      border: 'border-slate-700',
      icon: <Clock className="w-3 h-3" />,
    },
  };

  const cfg = configs[s] || {
    bg: 'bg-slate-800',
    text: 'text-slate-300',
    border: 'border-slate-700',
    icon: null,
  };

  const pad = size === 'sm' ? 'px-1.5 py-0.5 text-[9px]' : 'px-2 py-0.5 text-[10px]';

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-bold uppercase rounded border ${pad} ${cfg.bg} ${cfg.text} ${cfg.border}`}
    >
      {cfg.icon}
      <span>{s}</span>
    </span>
  );
};
