import React from 'react';
import { ActiveTab } from '../types';
import {
  Activity,
  Layers,
  Sparkles,
  Scissors,
  UserCheck,
  Trophy,
  Server
} from 'lucide-react';

interface NavbarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  backendConnected: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  backendConnected,
}) => {
  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'motion-lab', label: 'Motion Lab', icon: <Layers className="w-4 h-4" />, badge: '30 Trials' },
    { id: 'denoising', label: 'Denoising', icon: <Sparkles className="w-4 h-4 text-cyan-400" />, badge: '30%' },
    { id: 'gap-filling', label: 'Gap Filling', icon: <Scissors className="w-4 h-4 text-emerald-400" />, badge: '30%' },
    { id: 'retargeting', label: 'Retargeting', icon: <UserCheck className="w-4 h-4 text-purple-400" />, badge: '40%' },
    { id: 'competition', label: 'Competition Studio', icon: <Trophy className="w-4 h-4 text-amber-400" /> },
  ];

  return (
    <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 py-2.5 flex items-center justify-between select-none z-30">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 font-black text-white text-base">
          M
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-base tracking-wider text-slate-100 font-mono">MOTIONFORGE</span>
            <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
              v1.0.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400">Clean. Complete. Retarget.</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-slate-800 to-slate-750 text-white shadow-sm border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Backend Status Indicator */}
      <div className="flex items-center gap-2 bg-slate-950/50 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
        <Server className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-slate-400">Backend:</span>
        {backendConnected ? (
          <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Connected (127.0.0.1:8000)
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-rose-400 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            Connecting...
          </span>
        )}
      </div>
    </header>
  );
};
