import React, { useState } from 'react';
import { MotionItem } from '../../types';
import { Search, Play, Clock, Film, Layers, CheckCircle2, Database } from 'lucide-react';

interface MotionLabViewProps {
  motions: MotionItem[];
  selectedMotionId: string;
  onSelectMotion: (motionId: string) => void;
  onLoadBVH: (motionId: string, variant: 'clean' | 'denoising' | 'gap_filling' | 'retargeting', subvariant?: string) => void;
}

export const MotionLabView: React.FC<MotionLabViewProps> = ({
  motions,
  selectedMotionId,
  onSelectMotion,
  onLoadBVH,
}) => {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  const categories = ['All', 'Walking', 'Running', 'Jumping', 'Dance', 'Martial Arts & Acrobatics'];

  const filteredMotions = motions.filter((m) => {
    const matchesSearch =
      m.motion_id.toLowerCase().includes(search.toLowerCase()) ||
      m.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      selectedCategory === 'All' || m.category.toLowerCase() === selectedCategory.toLowerCase();
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="flex flex-col h-full p-4 sm:p-5 overflow-hidden" style={{ backgroundColor: 'var(--bg-page)' }}>
      {/* Top Bar: Search & Category Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3.5 border-b" style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center text-cyan-400">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-theme-primary flex items-center gap-2">
              <span>Motion Capture Dataset Explorer</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-theme-card text-cyan-400 border border-theme">
                {filteredMotions.length} / {motions.length} Trials
              </span>
            </h2>
            <p className="text-[11px] text-theme-muted">
              Standardized CMU optical motion trials (31 anatomical joints, 96 channels, 120.0 FPS)
            </p>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-theme-muted" />
          <input
            type="text"
            placeholder="Search motions (e.g. walk, jump, salsa)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-theme-card border border-theme rounded-lg pl-8 pr-3 py-1.5 text-xs text-theme-secondary placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
          />
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className="flex items-center gap-1.5 py-2.5 overflow-x-auto">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap transition-colors ${
              selectedCategory === cat
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                : 'bg-theme-card text-theme-muted hover:text-theme-secondary border border-slate-800'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Motions Grid */}
      <div className="flex-1 overflow-y-auto pr-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
        {filteredMotions.map((m) => {
          const isSelected = m.motion_id === selectedMotionId;

          return (
            <div
              key={m.motion_id}
              onClick={() => onSelectMotion(m.motion_id)}
              className={`rounded-xl p-3.5 flex flex-col justify-between transition-all cursor-pointer border ${
                isSelected
                  ? 'bg-theme-card border-cyan-500/60 shadow-md shadow-cyan-500/10'
                  : 'bg-theme-card-alt border-theme hover:border-slate-700 hover:bg-theme-hover/70'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono font-bold text-xs text-cyan-400">
                    {m.motion_id}
                  </span>
                  <span className="text-[9px] font-medium px-2 py-0.5 rounded-full bg-theme-inset text-theme-muted border border-theme-sub">
                    {m.category}
                  </span>
                </div>

                <h4 className="text-xs font-semibold text-theme-secondary capitalize line-clamp-1 mb-2.5">
                  {m.description}
                </h4>

                <div className="grid grid-cols-2 gap-1.5 text-[10px] text-theme-muted bg-slate-950/50 p-2 rounded-lg border border-theme-sub mb-3 font-mono">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-theme-muted" />
                    <span>{m.duration_seconds.toFixed(2)}s</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Film className="w-3 h-3 text-theme-muted" />
                    <span>{m.frame_count} frames</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Layers className="w-3 h-3 text-theme-muted" />
                    <span>31 Joints</span>
                  </div>
                  <div className="flex items-center gap-1 text-cyan-400">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>120.0 FPS</span>
                  </div>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectMotion(m.motion_id);
                  onLoadBVH(m.motion_id, 'clean');
                }}
                className="w-full py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-theme-primary font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-sm"
              >
                <Play className="w-3 h-3 fill-current" /> Load in 3D Viewer
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
