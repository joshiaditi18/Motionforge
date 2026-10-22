import React, { useState, useEffect, useRef } from 'react';
import { ActiveTab, ViewMode, CameraPreset, MotionItem } from './types';
import { fetchHealth, fetchMotions, fetchMotionBVH } from './services/api';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ThreeViewer, ThreeViewerRef } from './components/ThreeViewer';
import { PlaybackControls } from './components/PlaybackControls';
import { OverviewView } from './components/views/OverviewView';
import { MotionLabView } from './components/views/MotionLabView';
import { DenoisingView } from './components/views/DenoisingView';
import { GapFillingView } from './components/views/GapFillingView';
import { RetargetingView } from './components/views/RetargetingView';
import { AccuracyLabView } from './components/views/AccuracyLabView';
import { CompetitionView } from './components/views/CompetitionView';
import { GuidedDemoView } from './components/views/GuidedDemoView';
import { ResearchView } from './components/views/ResearchView';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);
  const [backendConnected, setBackendConnected] = useState<boolean>(false);
  const [motions, setMotions] = useState<MotionItem[]>([]);
  const [selectedMotionId, setSelectedMotionId] = useState<string>('MF001');

  // BVH & Visualization State
  const [primaryBVH, setPrimaryBVH] = useState<string | null>(null);
  const [secondaryBVH, setSecondaryBVH] = useState<string | null>(null);
  const [primaryLabel, setPrimaryLabel] = useState<string>('Input Motion');
  const [secondaryLabel, setSecondaryLabel] = useState<string>('Algorithm Output');
  const [viewMode, setViewMode] = useState<ViewMode>('side-by-side');

  // Playback & Gap State
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [totalFrames, setTotalFrames] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [gapInterval, setGapInterval] = useState<[number, number] | null>(null);

  const viewerRef = useRef<ThreeViewerRef>(null);

  // Check backend health & fetch motions
  useEffect(() => {
    const initApp = async () => {
      try {
        await fetchHealth();
        setBackendConnected(true);
      } catch (err) {
        console.warn('Backend not responding yet:', err);
        setBackendConnected(false);
      }

      try {
        const motionList = await fetchMotions();
        setMotions(motionList);
        if (motionList.length > 0) {
          const initialId = motionList[0].motion_id;
          setSelectedMotionId(initialId);
          loadMotionBVH(initialId, 'clean');
        }
      } catch (err) {
        console.error('Failed to load motions:', err);
      }
    };

    initApp();
    const interval = setInterval(() => {
      fetchHealth()
        .then(() => setBackendConnected(true))
        .catch(() => setBackendConnected(false));
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Clear gap interval when switching away from gap filling
  useEffect(() => {
    if (activeTab !== 'gap-filling') {
      setGapInterval(null);
    }
  }, [activeTab]);

  const loadMotionBVH = async (
    motionId: string,
    variant: 'clean' | 'denoising' | 'gap_filling' | 'retargeting',
    subvariant?: string
  ) => {
    try {
      const bvh = await fetchMotionBVH(motionId, variant, subvariant);
      setPrimaryBVH(bvh);
      setSecondaryBVH(null);
      setPrimaryLabel(`${motionId} (${variant}${subvariant ? ` - ${subvariant}` : ''})`);
      setViewMode('single');
      setTimeout(() => {
        viewerRef.current?.play();
        setIsPlaying(true);
      }, 100);
    } catch (err) {
      console.error('Failed to load BVH file:', err);
    }
  };

  const handleSetDualBVH = (primary: string, secondary?: string) => {
    setPrimaryBVH(primary);
    if (secondary) {
      setSecondaryBVH(secondary);
      setViewMode('side-by-side');
      setPrimaryLabel('Input / Unprocessed');
      setSecondaryLabel('Algorithm Output');
    } else {
      setSecondaryBVH(null);
      setViewMode('single');
    }
    setTimeout(() => {
      viewerRef.current?.play();
      setIsPlaying(true);
    }, 100);
  };

  // Playback Control Handlers
  const handlePlayToggle = () => {
    if (isPlaying) {
      viewerRef.current?.pause();
      setIsPlaying(false);
    } else {
      viewerRef.current?.play();
      setIsPlaying(true);
    }
  };

  const handleSeek = (normalized: number) => {
    viewerRef.current?.seek(normalized);
  };

  const handleStepFrame = (dir: number) => {
    viewerRef.current?.seekFrame(currentFrame + dir);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    viewerRef.current?.setSpeed(speed);
  };

  const handleCameraPreset = (preset: CameraPreset) => {
    viewerRef.current?.setCameraPreset(preset);
  };

  const handleToggleGrid = () => {
    viewerRef.current?.toggleGrid();
  };

  const handleResetCamera = () => {
    viewerRef.current?.resetCamera();
  };

  const handleFitSkeleton = () => {
    viewerRef.current?.fitToSkeleton();
  };

  const handleTimeUpdate = (cur: number, dur: number, frame: number, total: number) => {
    setCurrentTime(cur);
    setDuration(dur);
    setCurrentFrame(frame);
    setTotalFrames(total);
  };

  const showViewport = activeTab !== 'overview' && activeTab !== 'competition' && activeTab !== 'demo' && activeTab !== 'research';

  return (
    <div className="flex h-screen w-screen overflow-hidden font-sans antialiased" style={{ backgroundColor: 'var(--bg-page)', color: 'var(--text-primary)' }}>
      {/* Collapsible Scientific Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setMobileSidebarOpen(false);
        }}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        motionCount={motions.length}
      />

      {/* Mobile Drawer Backdrop */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Main Column */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Top Header */}
        <Header
          activeTab={activeTab}
          onMobileMenuToggle={() => setMobileSidebarOpen(!mobileSidebarOpen)}
          backendConnected={backendConnected}
          motions={motions}
          selectedMotionId={selectedMotionId}
          onSelectMotion={(id) => {
            setSelectedMotionId(id);
            loadMotionBVH(id, 'clean');
          }}
          onFitSkeleton={handleFitSkeleton}
          onToggleGrid={handleToggleGrid}
          onResetCamera={handleResetCamera}
          onCameraPreset={handleCameraPreset}
        />

        {/* Viewport & View Panels */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Full-Page Views */}
          {activeTab === 'overview' && (
            <div className="flex-1 overflow-y-auto">
              <OverviewView onNavigate={setActiveTab} motions={motions} />
            </div>
          )}

          {activeTab === 'competition' && (
            <div className="flex-1 overflow-y-auto">
              <CompetitionView />
            </div>
          )}

          {activeTab === 'demo' && (
            <div className="flex-1 overflow-y-auto">
              <GuidedDemoView
                motions={motions}
                onSetBVH={handleSetDualBVH}
                onViewModeChange={setViewMode}
                onNavigate={setActiveTab}
              />
            </div>
          )}

          {activeTab === 'research' && (
            <div className="flex-1 overflow-y-auto">
              <ResearchView />
            </div>
          )}

          {/* 3D Viewport + Interactive Workbench Split Views */}
          {showViewport && (
            <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
              {/* Left / Upper: 3D Character Viewport + Controls */}
              <div
                className="flex-1 flex flex-col h-[52%] lg:h-full border-b lg:border-b-0 lg:border-r"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--viewport-bg)' }}
              >
                <div className="flex-1 relative min-h-0">
                  <ThreeViewer
                    ref={viewerRef}
                    primaryBVH={primaryBVH}
                    secondaryBVH={secondaryBVH}
                    viewMode={viewMode}
                    primaryLabel={primaryLabel}
                    secondaryLabel={secondaryLabel}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadSample={() => loadMotionBVH('MF001', 'clean')}
                  />
                </div>

                {/* Playback Scrubber & Controls */}
                <PlaybackControls
                  isPlaying={isPlaying}
                  currentTime={currentTime}
                  duration={duration}
                  currentFrame={currentFrame}
                  totalFrames={totalFrames}
                  playbackSpeed={playbackSpeed}
                  viewMode={viewMode}
                  hasSecondary={!!secondaryBVH}
                  gapInterval={gapInterval}
                  onPlayToggle={handlePlayToggle}
                  onSeek={handleSeek}
                  onStepFrame={handleStepFrame}
                  onSpeedChange={handleSpeedChange}
                  onViewModeChange={setViewMode}
                  onCameraPreset={handleCameraPreset}
                  onToggleGrid={handleToggleGrid}
                  onResetCamera={handleResetCamera}
                />
              </div>

              {/* Right / Lower: Interactive Task Workbench */}
              <div
                className="w-full lg:w-[480px] xl:w-[540px] 2xl:w-[580px] h-[48%] lg:h-full flex flex-col overflow-hidden border-t lg:border-t-0"
                style={{ backgroundColor: 'var(--bg-card-alt)', borderColor: 'var(--border-default)' }}
              >
                {activeTab === 'motion-lab' && (
                  <MotionLabView
                    motions={motions}
                    selectedMotionId={selectedMotionId}
                    onSelectMotion={(id) => {
                      setSelectedMotionId(id);
                      loadMotionBVH(id, 'clean');
                    }}
                    onLoadBVH={loadMotionBVH}
                  />
                )}

                {activeTab === 'denoising' && (
                  <DenoisingView
                    motions={motions}
                    selectedMotionId={selectedMotionId}
                    onSelectMotion={setSelectedMotionId}
                    onSetBVH={handleSetDualBVH}
                    onViewModeChange={setViewMode}
                  />
                )}

                {activeTab === 'gap-filling' && (
                  <GapFillingView
                    motions={motions}
                    selectedMotionId={selectedMotionId}
                    onSelectMotion={setSelectedMotionId}
                    onSetBVH={handleSetDualBVH}
                    onViewModeChange={setViewMode}
                    onSetGapInterval={setGapInterval}
                  />
                )}

                {activeTab === 'retargeting' && (
                  <RetargetingView
                    motions={motions}
                    selectedMotionId={selectedMotionId}
                    onSelectMotion={setSelectedMotionId}
                    onSetBVH={handleSetDualBVH}
                    onViewModeChange={setViewMode}
                  />
                )}

                {activeTab === 'accuracy-lab' && (
                  <AccuracyLabView
                    motions={motions}
                    selectedMotionId={selectedMotionId}
                    onSelectMotion={setSelectedMotionId}
                    onSetBVH={handleSetDualBVH}
                    onViewModeChange={setViewMode}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
