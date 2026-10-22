import React from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Grid,
  Layers,
  Columns,
  Maximize2,
  Compass,
} from 'lucide-react';
import { ViewMode, CameraPreset } from '../types';

interface PlaybackControlsProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  currentFrame: number;
  totalFrames: number;
  playbackSpeed: number;
  viewMode: ViewMode;
  hasSecondary: boolean;
  gapInterval?: [number, number] | null;
  onPlayToggle: () => void;
  onSeek: (normalized: number) => void;
  onStepFrame: (direction: number) => void;
  onSpeedChange: (speed: number) => void;
  onViewModeChange: (mode: ViewMode) => void;
  onCameraPreset: (preset: CameraPreset) => void;
  onToggleGrid: () => void;
  onResetCamera: () => void;
}

export const PlaybackControls: React.FC<PlaybackControlsProps> = ({
  isPlaying,
  currentTime,
  duration,
  currentFrame,
  totalFrames,
  playbackSpeed,
  viewMode,
  hasSecondary,
  gapInterval,
  onPlayToggle,
  onSeek,
  onStepFrame,
  onSpeedChange,
  onViewModeChange,
  onCameraPreset,
  onToggleGrid,
  onResetCamera,
}) => {
  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const rem = (secs % 60).toFixed(2);
    return `${mins}:${rem.padStart(5, '0')}`;
  };

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  // Gap interval on timeline
  let gapStartPct = 0;
  let gapWidthPct = 0;
  if (gapInterval && totalFrames > 0) {
    const [gStart, gEnd] = gapInterval;
    gapStartPct = (Math.max(0, gStart) / totalFrames) * 100;
    gapWidthPct = (Math.max(0, gEnd - gStart) / totalFrames) * 100;
  }

  return (
    <div
      className="border-t px-4 py-2.5 flex flex-col gap-2 select-none z-10 shrink-0 transition-colors duration-200"
      style={{
        backgroundColor: 'var(--bg-sidebar)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* Timeline Scrubber */}
      <div className="flex items-center gap-3">
        <span
          className="text-[11px] font-mono min-w-[55px] font-semibold"
          style={{ color: 'var(--accent-text)' }}
        >
          {formatTime(currentTime)}
        </span>

        {/* Timeline track container */}
        <div className="relative flex-1 flex items-center h-4 group">
          {/* Background track */}
          <div
            className="absolute inset-x-0 h-1.5 rounded-full overflow-hidden pointer-events-none"
            style={{ backgroundColor: 'var(--bg-inset)' }}
          >
            {/* Gap Interval Highlight on timeline */}
            {gapInterval && gapWidthPct > 0 && (
              <div
                className="absolute top-0 bottom-0 bg-rose-500/60 border-x border-rose-400"
                style={{
                  left: `${gapStartPct}%`,
                  width: `${gapWidthPct}%`,
                }}
                title={`Missing Frame Gap: [${gapInterval[0]} - ${gapInterval[1]}]`}
              />
            )}
          </div>

          <input
            type="range"
            min={0}
            max={100}
            step={0.05}
            value={progressPercent || 0}
            onChange={(e) => onSeek(parseFloat(e.target.value) / 100)}
            className="relative z-10 w-full h-2 bg-transparent appearance-none cursor-pointer accent-cyan-400 hover:accent-cyan-300 transition-all focus:outline-none"
          />
        </div>

        <span
          className="text-[11px] font-mono min-w-[125px] text-right font-medium"
          style={{ color: 'var(--text-muted)' }}
        >
          {formatTime(duration)} ({currentFrame}/{totalFrames}f)
        </span>
      </div>

      {/* Main Buttons Bar */}
      <div className="flex items-center justify-between gap-2">
        {/* Left: Playback buttons */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onStepFrame(-1)}
            title="Step Back 1 Frame (Left Arrow)"
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onPlayToggle}
            className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-sm shadow-cyan-600/30 transition-all"
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-current" /> Pause
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" /> Play
              </>
            )}
          </button>

          <button
            onClick={() => onStepFrame(1)}
            title="Step Forward 1 Frame (Right Arrow)"
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          {/* Speed Selector */}
          <div
            className="ml-1.5 flex items-center gap-1 px-2 py-1 rounded-lg border text-[11px]"
            style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-default)' }}
          >
            <span className="font-mono" style={{ color: 'var(--text-muted)' }}>Speed:</span>
            <select
              value={playbackSpeed}
              onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
              className="bg-transparent font-mono font-semibold outline-none cursor-pointer"
              style={{ color: 'var(--accent-text)' }}
            >
              <option value="0.25" style={{ backgroundColor: 'var(--bg-input)', color: 'var(--text-secondary)' }}>0.25x</option>
              <option value="0.5"  style={{ backgroundColor: 'var(--bg-input)', color: 'var(--text-secondary)' }}>0.5x</option>
              <option value="1.0"  style={{ backgroundColor: 'var(--bg-input)', color: 'var(--text-secondary)' }}>1.0x</option>
              <option value="1.5"  style={{ backgroundColor: 'var(--bg-input)', color: 'var(--text-secondary)' }}>1.5x</option>
              <option value="2.0"  style={{ backgroundColor: 'var(--bg-input)', color: 'var(--text-secondary)' }}>2.0x</option>
            </select>
          </div>
        </div>

        {/* Center: View Mode (if secondary motion available) */}
        {hasSecondary && (
          <div
            className="flex items-center rounded-lg p-0.5 border"
            style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-default)' }}
          >
            {(['single', 'side-by-side', 'overlay'] as ViewMode[]).map((mode) => {
              const label = mode === 'single' ? 'Single' : mode === 'side-by-side' ? 'Side-by-Side' : 'Overlay';
              const icon = mode === 'single' ? <Maximize2 className="w-3 h-3" /> : mode === 'side-by-side' ? <Columns className="w-3 h-3" /> : <Layers className="w-3 h-3" />;
              return (
                <button
                  key={mode}
                  onClick={() => onViewModeChange(mode)}
                  className="px-2.5 py-1 rounded text-[11px] font-medium flex items-center gap-1.5 transition-colors"
                  style={
                    viewMode === mode
                      ? { backgroundColor: 'var(--accent)', color: '#ffffff', fontWeight: 600 }
                      : { color: 'var(--text-muted)' }
                  }
                >
                  {icon} {label}
                </button>
              );
            })}
          </div>
        )}

        {/* Right: Camera Presets & Utilities */}
        <div className="flex items-center gap-1.5">
          <div
            className="flex items-center rounded-lg border px-1 py-0.5 text-xs"
            style={{ backgroundColor: 'var(--bg-inset)', borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }}
          >
            <Compass className="w-3.5 h-3.5 mr-1" style={{ color: 'var(--text-muted)' }} />
            {(['perspective', 'front', 'side', 'top'] as CameraPreset[]).map((preset, idx, arr) => (
              <React.Fragment key={preset}>
                <button
                  onClick={() => onCameraPreset(preset)}
                  className="px-1.5 py-0.5 text-[11px] font-mono transition-colors hover:text-cyan-500"
                  title={{ perspective: '3D Free Orbit', front: 'Front Orthographic (+Z)', side: 'Side Profile (+X)', top: 'Top View (+Y)' }[preset]}
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {{ perspective: '3D', front: 'Front', side: 'Side', top: 'Top' }[preset]}
                </button>
                {idx < arr.length - 1 && (
                  <span style={{ color: 'var(--border-strong)' }}>|</span>
                )}
              </React.Fragment>
            ))}
          </div>

          <button
            onClick={onToggleGrid}
            title="Toggle Floor Grid"
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <Grid className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onResetCamera}
            title="Reset Camera View"
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
