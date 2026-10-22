import React from 'react';
import { ActiveTab, MotionItem, CameraPreset } from '../types';
import {
  Menu,
  Server,
  Maximize,
  Grid,
  ChevronDown,
  RotateCcw,
  Sun,
  Moon,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface HeaderProps {
  activeTab: ActiveTab;
  onMobileMenuToggle: () => void;
  backendConnected: boolean;
  motions: MotionItem[];
  selectedMotionId: string;
  onSelectMotion: (motionId: string) => void;
  onFitSkeleton: () => void;
  onToggleGrid: () => void;
  onResetCamera: () => void;
  onCameraPreset: (preset: CameraPreset) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onMobileMenuToggle,
  backendConnected,
  motions,
  selectedMotionId,
  onSelectMotion,
  onFitSkeleton,
  onToggleGrid,
  onResetCamera,
  onCameraPreset,
}) => {
  const { theme, toggleTheme } = useTheme();

  const pageTitles: Record<ActiveTab, { title: string; category: string }> = {
    overview: { title: 'Project Overview & Metrics Dashboard', category: 'Dashboard' },
    'motion-lab': { title: 'Motion Dataset Explorer (30 Trials)', category: 'Dataset' },
    denoising: { title: 'Task 1: Motion Denoising Workbench', category: 'Track 1 (30%)' },
    'gap-filling': { title: 'Task 2: Motion Gap-Filling Workbench', category: 'Track 2 (30%)' },
    retargeting: { title: 'Task 3: Cross-Morphology Retargeting', category: 'Track 3 (40%)' },
    'accuracy-lab': { title: 'Algorithm Accuracy & Comparative Benchmarks', category: 'Phase 11' },
    competition: { title: 'Competition Runner & Evaluation Studio', category: 'Audit' },
    demo: { title: 'Guided Demonstration & Interactive Pipeline', category: 'Demo' },
    research: { title: 'Scientific Methodology & Research Findings', category: 'Research' },
  };

  const currentMotion = motions.find((m) => m.motion_id === selectedMotionId);
  const info = pageTitles[activeTab] || { title: 'MOTIONFORGE', category: 'Workbench' };

  return (
    <header
      className="h-14 border-b px-4 flex items-center justify-between select-none z-20 shrink-0 transition-colors duration-200"
      style={{
        backgroundColor: 'var(--bg-header)',
        borderColor: 'var(--border-default)',
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Left: Mobile Toggle + Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileMenuToggle}
          className="md:hidden p-1.5 rounded-lg transition-colors"
          style={{ color: 'var(--text-muted)' }}
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex flex-col">
          <div className="flex items-center gap-1.5 text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
            <span>MOTIONFORGE</span>
            <span>/</span>
            <span style={{ color: 'var(--accent-text)' }} className="font-medium">{info.category}</span>
          </div>
          <h2
            className="text-xs font-bold tracking-wide truncate max-w-xs sm:max-w-md"
            style={{ color: 'var(--text-primary)' }}
          >
            {info.title}
          </h2>
        </div>
      </div>

      {/* Center/Right: Context Actions */}
      <div className="flex items-center gap-2.5">
        {/* Motion Selector Pill (for workbenches) */}
        {activeTab !== 'overview' && activeTab !== 'competition' && activeTab !== 'demo' && activeTab !== 'research' && motions.length > 0 && (
          <div
            className="flex items-center rounded-lg px-2.5 py-1 text-xs border"
            style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-default)' }}
          >
            <span
              className="text-[10px] mr-2 font-mono hidden sm:inline"
              style={{ color: 'var(--text-muted)' }}
            >
              Motion:
            </span>
            <select
              value={selectedMotionId}
              onChange={(e) => onSelectMotion(e.target.value)}
              className="bg-transparent font-mono font-medium text-xs outline-none cursor-pointer"
              style={{ color: 'var(--accent-text)' }}
            >
              {motions.map((m) => (
                <option
                  key={m.motion_id}
                  value={m.motion_id}
                  style={{ backgroundColor: 'var(--bg-input)', color: 'var(--text-secondary)' }}
                >
                  {m.motion_id} — {m.description.slice(0, 24)} ({m.frame_count}f)
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Viewport Quick Actions (if viewer is active) */}
        {activeTab !== 'overview' && activeTab !== 'competition' && activeTab !== 'demo' && activeTab !== 'research' && (
          <div
            className="hidden sm:flex items-center gap-1 p-0.5 rounded-lg border"
            style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-default)' }}
          >
            <button
              onClick={onFitSkeleton}
              title="Fit View to Skeleton Bounds"
              className="px-2 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-text)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            >
              <Maximize className="w-3 h-3" /> Fit
            </button>
            <button
              onClick={onToggleGrid}
              title="Toggle Ground Grid"
              className="p-1.5 rounded transition-colors"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onResetCamera}
              title="Reset View"
              className="p-1.5 rounded transition-colors"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="p-1.5 rounded-lg border transition-all duration-200 flex items-center justify-center"
          style={{
            backgroundColor: 'var(--bg-inset)',
            borderColor: 'var(--border-default)',
            color: theme === 'light' ? 'var(--warning-text)' : 'var(--text-muted)',
          }}
        >
          {theme === 'dark' ? (
            <Sun className="w-3.5 h-3.5" />
          ) : (
            <Moon className="w-3.5 h-3.5" />
          )}
        </button>

        {/* Backend Status Pill */}
        <div
          title={backendConnected ? 'Backend service online at http://127.0.0.1:8000' : 'Backend service disconnected'}
          className="px-2.5 py-1 rounded-lg border flex items-center gap-1.5 text-[11px] font-mono transition-colors"
          style={{
            backgroundColor: backendConnected ? 'var(--success-bg)' : 'var(--error-bg)',
            borderColor: backendConnected ? 'var(--success-border)' : 'var(--error-border)',
            color: backendConnected ? 'var(--success-text)' : 'var(--error-text)',
          }}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${backendConnected ? 'animate-pulse' : ''}`}
            style={{ backgroundColor: backendConnected ? 'var(--success-text)' : 'var(--error-text)' }}
          />
          <span className="hidden sm:inline font-semibold">
            {backendConnected ? 'Backend Online' : 'Connecting'}
          </span>
          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>:8000</span>
        </div>
      </div>
    </header>
  );
};
