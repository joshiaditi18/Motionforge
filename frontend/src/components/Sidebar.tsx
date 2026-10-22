import React from 'react';
import { ActiveTab } from '../types';
import {
  LayoutDashboard,
  Layers,
  Sparkles,
  Scissors,
  UserCheck,
  Trophy,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Database,
  Cpu,
  Activity,
  Compass,
  FlaskConical,
} from 'lucide-react';

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  motionCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  collapsed,
  onToggleCollapse,
  motionCount,
}) => {
  const navItems = [
    {
      id: 'overview' as ActiveTab,
      label: 'Overview',
      shortLabel: 'Overview',
      icon: <LayoutDashboard className="w-4 h-4 shrink-0" />,
      tag: null,
    },
    {
      id: 'motion-lab' as ActiveTab,
      label: 'Motion Lab',
      shortLabel: 'Lab',
      icon: <Layers className="w-4 h-4 shrink-0" style={{ color: 'var(--accent-text)' }} />,
      tag: `${motionCount || 30}`,
    },
    {
      id: 'denoising' as ActiveTab,
      label: 'Denoising',
      shortLabel: 'Task 1',
      icon: <Sparkles className="w-4 h-4 shrink-0" style={{ color: 'var(--accent-text)' }} />,
      tag: '30%',
    },
    {
      id: 'gap-filling' as ActiveTab,
      label: 'Gap Filling',
      shortLabel: 'Task 2',
      icon: <Scissors className="w-4 h-4 shrink-0 text-emerald-400" />,
      tag: '30%',
    },
    {
      id: 'retargeting' as ActiveTab,
      label: 'Retargeting',
      shortLabel: 'Task 3',
      icon: <UserCheck className="w-4 h-4 shrink-0 text-purple-400" />,
      tag: '40%',
    },
    {
      id: 'accuracy-lab' as ActiveTab,
      label: 'Accuracy Lab',
      shortLabel: 'Accuracy',
      icon: <Activity className="w-4 h-4 shrink-0 text-rose-400" />,
      tag: 'Bench',
    },
    {
      id: 'competition' as ActiveTab,
      label: 'Competition Studio',
      shortLabel: 'Studio',
      icon: <Trophy className="w-4 h-4 shrink-0 text-amber-400" />,
      tag: 'Phases 5-6',
    },
    {
      id: 'demo' as ActiveTab,
      label: 'Guided Demo',
      shortLabel: 'Demo',
      icon: <Compass className="w-4 h-4 shrink-0 text-violet-400" />,
      tag: 'Interactive',
    },
    {
      id: 'research' as ActiveTab,
      label: 'Research Methodology',
      shortLabel: 'Research',
      icon: <FlaskConical className="w-4 h-4 shrink-0 text-amber-400" />,
      tag: 'Phase 12',
    },
  ];

  return (
    <aside
      className={`flex flex-col justify-between transition-all duration-300 select-none z-30 shrink-0 border-r ${
        collapsed ? 'w-16' : 'w-60'
      }`}
      style={{
        backgroundColor: 'var(--bg-sidebar)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* Top: Logo & Nav items */}
      <div className="flex flex-col">
        {/* Logo / Brand header */}
        <div
          className="h-14 border-b px-3.5 flex items-center justify-between"
          style={{ borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center font-mono font-black text-white text-sm shrink-0 shadow-sm shadow-cyan-500/20">
              MF
            </div>
            {!collapsed && (
              <div className="flex flex-col truncate">
                <span
                  className="font-mono font-bold text-xs tracking-wider"
                  style={{ color: 'var(--text-primary)' }}
                >
                  MOTIONFORGE
                </span>
                <span
                  className="text-[10px] tracking-tight font-medium"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Kinematics Suite
                </span>
              </div>
            )}
          </div>

          {!collapsed && (
            <button
              onClick={onToggleCollapse}
              title="Collapse Sidebar"
              className="p-1 rounded transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Navigation list */}
        <nav className="p-2 space-y-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                title={collapsed ? item.label : undefined}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group relative"
                style={{
                  backgroundColor: isActive ? 'var(--bg-hover)' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  border: isActive ? '1px solid var(--border-strong)' : '1px solid transparent',
                  fontWeight: isActive ? 600 : 500,
                }}
                onMouseEnter={e => {
                  if (!isActive) {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-hover)';
                    (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                  }
                }}
                onMouseLeave={e => {
                  if (!isActive) {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                    (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
                  }
                }}
              >
                {/* Active indicator bar */}
                {isActive && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r"
                    style={{ backgroundColor: 'var(--accent)' }}
                  />
                )}

                {item.icon}

                {!collapsed && (
                  <span className="flex-1 text-left truncate">{item.label}</span>
                )}

                {!collapsed && item.tag && (
                  <span
                    className="text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold shrink-0"
                    style={
                      isActive
                        ? {
                            backgroundColor: 'var(--accent-bg)',
                            color: 'var(--accent-text)',
                            border: '1px solid var(--accent-border)',
                          }
                        : {
                            backgroundColor: 'var(--bg-inset)',
                            color: 'var(--text-muted)',
                            border: '1px solid transparent',
                          }
                    }
                  >
                    {item.tag}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom: Technical metadata & Collapse Toggle */}
      <div
        className="p-2 border-t flex flex-col gap-1.5"
        style={{ borderColor: 'var(--border-default)' }}
      >
        {!collapsed && (
          <div
            className="p-2.5 rounded-lg border text-[10px] space-y-1"
            style={{
              backgroundColor: 'var(--bg-inset)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            <div className="flex items-center justify-between" style={{ color: 'var(--text-secondary)' }}>
              <span className="flex items-center gap-1 font-mono">
                <Cpu className="w-3 h-3" style={{ color: 'var(--accent-text)' }} /> Sampling:
              </span>
              <span className="font-mono font-semibold" style={{ color: 'var(--accent-text)' }}>120.0 FPS</span>
            </div>
            <div className="flex items-center justify-between" style={{ color: 'var(--text-secondary)' }}>
              <span className="flex items-center gap-1 font-mono">
                <Database className="w-3 h-3 text-emerald-500" /> Channels:
              </span>
              <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>96 Intrinsic</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between px-1">
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            title="FastAPI Interactive Docs"
            className={`flex items-center gap-2 p-1.5 rounded text-[11px] transition-colors ${
              collapsed ? 'w-full justify-center' : ''
            }`}
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-text)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <BookOpen className="w-3.5 h-3.5 shrink-0" />
            {!collapsed && <span>API Docs</span>}
          </a>

          {collapsed && (
            <button
              onClick={onToggleCollapse}
              title="Expand Sidebar"
              className="p-1.5 rounded transition-colors w-full flex justify-center mt-1"
              style={{ color: 'var(--text-muted)' }}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}

          {!collapsed && (
            <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>v1.0.0</span>
          )}
        </div>
      </div>
    </aside>
  );
};
