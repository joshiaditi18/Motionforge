import React, { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { BVHLoader } from 'three/examples/jsm/loaders/BVHLoader.js';
import { ViewMode, CameraPreset } from '../types';
import { Maximize, Eye, Info, Play } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export interface ThreeViewerRef {
  play: () => void;
  pause: () => void;
  seek: (normalizedTime: number) => void;
  seekFrame: (frame: number) => void;
  setSpeed: (speed: number) => void;
  setCameraPreset: (preset: CameraPreset) => void;
  toggleGrid: () => void;
  toggleTrails: () => void;
  resetCamera: () => void;
  fitToSkeleton: () => void;
}

interface ThreeViewerProps {
  primaryBVH: string | null;
  secondaryBVH?: string | null;
  viewMode: ViewMode;
  primaryLabel?: string;
  secondaryLabel?: string;
  onTimeUpdate?: (currentTime: number, duration: number, currentFrame: number, totalFrames: number) => void;
  onJointHover?: (jointName: string | null, worldPos: [number, number, number] | null) => void;
  onLoadSample?: () => void;
}

export const ThreeViewer = forwardRef<ThreeViewerRef, ThreeViewerProps>(({
  primaryBVH,
  secondaryBVH,
  viewMode,
  primaryLabel = 'Input Sequence',
  secondaryLabel = 'Processed Output',
  onTimeUpdate,
  onJointHover,
  onLoadSample,
}, ref) => {
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [hoveredJointInfo, setHoveredJointInfo] = useState<{
    name: string;
    parentName: string;
    pos: [number, number, number];
  } | null>(null);

  // Three.js internal references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const gridRef = useRef<THREE.GridHelper | null>(null);
  const clockRef = useRef(new THREE.Clock());
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());

  // Interactive meshes for picking
  const jointMeshesRef = useRef<THREE.Mesh[]>([]);

  // Animation objects
  const mixer1Ref = useRef<THREE.AnimationMixer | null>(null);
  const mixer2Ref = useRef<THREE.AnimationMixer | null>(null);
  const action1Ref = useRef<THREE.AnimationAction | null>(null);
  const action2Ref = useRef<THREE.AnimationAction | null>(null);
  const group1Ref = useRef<THREE.Group | null>(null);
  const group2Ref = useRef<THREE.Group | null>(null);
  const skeletonHelper1Ref = useRef<THREE.SkeletonHelper | null>(null);
  const skeletonHelper2Ref = useRef<THREE.SkeletonHelper | null>(null);

  const durationRef = useRef(0);
  const totalFramesRef = useRef(0);
  const isPlayingRef = useRef(false);
  const playbackSpeedRef = useRef(1.0);

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    // Scene with dark graphite aesthetic
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070b13);
    scene.fog = new THREE.FogExp2(0x070b13, 0.0018);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 1, 3500);
    camera.position.set(0, 85, 230);
    cameraRef.current = camera;

    // High performance WebGL renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.maxPolarAngle = Math.PI / 2 + 0.04; // Keep camera above ground
    controls.minDistance = 20;
    controls.maxDistance = 700;
    controls.target.set(0, 42, 0);
    controlsRef.current = controls;

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.25);
    dirLight1.position.set(140, 220, 160);
    dirLight1.castShadow = true;
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xa855f7, 0.7);
    dirLight2.position.set(-140, 160, -120);
    scene.add(dirLight2);

    // Floor Grid with subtle scientific markings
    const grid = new THREE.GridHelper(500, 50, 0x0284c7, 0x1e293b);
    grid.position.y = 0;
    scene.add(grid);
    gridRef.current = grid;

    // Ground plane
    const groundGeo = new THREE.PlaneGeometry(1200, 1200);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x050811,
      roughness: 0.92,
      metalness: 0.08,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = clockRef.current.getDelta();

      if (isPlayingRef.current) {
        if (mixer1Ref.current) mixer1Ref.current.update(delta);
        if (mixer2Ref.current) mixer2Ref.current.update(delta);

        if (action1Ref.current && durationRef.current > 0) {
          const curTime = action1Ref.current.time % durationRef.current;
          const curFrame = Math.round((curTime / durationRef.current) * totalFramesRef.current);
          if (onTimeUpdate) {
            onTimeUpdate(curTime, durationRef.current, curFrame, totalFramesRef.current);
          }
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Mouse Move for Raycasting Joint Inspection
    const handleMouseMove = (e: MouseEvent) => {
      if (!container) return;
      const rect = container.getBoundingClientRect();
      mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (cameraRef.current && jointMeshesRef.current.length > 0) {
        raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current);
        const intersects = raycasterRef.current.intersectObjects(jointMeshesRef.current, false);
        if (intersects.length > 0) {
          const hit = intersects[0].object;
          const bone = hit.parent as THREE.Bone;
          if (bone) {
            const worldPos = new THREE.Vector3();
            bone.getWorldPosition(worldPos);
            setHoveredJointInfo({
              name: bone.name,
              parentName: bone.parent?.name || 'Root (None)',
              pos: [
                parseFloat(worldPos.x.toFixed(2)),
                parseFloat(worldPos.y.toFixed(2)),
                parseFloat(worldPos.z.toFixed(2)),
              ],
            });
            if (onJointHover) {
              onJointHover(bone.name, [worldPos.x, worldPos.y, worldPos.z]);
            }
          }
        } else {
          setHoveredJointInfo(null);
          if (onJointHover) onJointHover(null, null);
        }
      }
    };
    container.addEventListener('mousemove', handleMouseMove);

    // Resize Handler
    const handleResize = () => {
      if (!container || !camera || !renderer) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      container.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update Three.js scene colors when theme changes (no remount)
  useEffect(() => {
    if (!sceneRef.current) return;
    const isDark = theme === 'dark';
    const bgColor  = isDark ? 0x070b13 : 0xe2e8f0;
    const fogColor = isDark ? 0x070b13 : 0xe2e8f0;
    sceneRef.current.background = new THREE.Color(bgColor);
    if (sceneRef.current.fog) {
      (sceneRef.current.fog as THREE.FogExp2).color.set(fogColor);
    }
    if (gridRef.current) {
      // Recreate grid material with new colors
      const gridPrimary   = isDark ? 0x0284c7 : 0x0891b2;
      const gridSecondary = isDark ? 0x1e293b : 0xcbd5e1;
      sceneRef.current.remove(gridRef.current);
      (gridRef.current as THREE.GridHelper).dispose?.();
      const newGrid = new THREE.GridHelper(500, 50, gridPrimary, gridSecondary);
      newGrid.position.y = 0;
      newGrid.visible = showGrid;
      sceneRef.current.add(newGrid);
      gridRef.current = newGrid;
    }
  }, [theme]);

  // Helper to construct visual skeleton model
  const buildSkeletonModel = (
    bvhString: string,
    lineColorHex: number,
    sphereColorHex: number,
    offsetX: number
  ) => {
    const loader = new BVHLoader();
    const result = loader.parse(bvhString);

    const group = new THREE.Group();
    group.position.x = offsetX;

    const rootBone = result.skeleton.bones[0];
    group.add(rootBone);

    // Skeleton wireframe
    const helper = new THREE.SkeletonHelper(rootBone);
    (helper as any).skeleton = result.skeleton;
    (helper.material as THREE.LineBasicMaterial).color = new THREE.Color(lineColorHex);
    (helper.material as THREE.LineBasicMaterial).linewidth = 3.5;
    (helper.material as THREE.LineBasicMaterial).depthTest = true;
    group.add(helper);

    // High precision joint spheres
    const sphereGeo = new THREE.SphereGeometry(1.25, 12, 12);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: sphereColorHex,
      emissive: sphereColorHex,
      emissiveIntensity: 0.5,
      roughness: 0.35,
    });

    const meshes: THREE.Mesh[] = [];
    result.skeleton.bones.forEach((bone) => {
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      bone.add(sphere);
      meshes.push(sphere);
    });

    // Mixer
    const mixer = new THREE.AnimationMixer(helper);
    const action = mixer.clipAction(result.clip);
    action.setEffectiveWeight(1.0);
    action.play();
    action.paused = !isPlayingRef.current;

    return {
      group,
      helper,
      mixer,
      action,
      duration: result.clip.duration,
      totalFrames: Math.round(result.clip.duration * 120),
      meshes,
    };
  };

  // Rebuild scene when BVH data or viewMode changes
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // Clean up previous groups
    if (group1Ref.current) scene.remove(group1Ref.current);
    if (mixer1Ref.current) mixer1Ref.current.stopAllAction();

    if (group2Ref.current) scene.remove(group2Ref.current);
    if (mixer2Ref.current) mixer2Ref.current.stopAllAction();

    jointMeshesRef.current = [];

    if (!primaryBVH) return;

    try {
      const isDual = !!secondaryBVH && (viewMode === 'side-by-side' || viewMode === 'overlay');
      const offset1 = isDual && viewMode === 'side-by-side' ? -40 : 0;
      const offset2 = isDual && viewMode === 'side-by-side' ? 40 : 0;

      // Primary Skeleton (Cyan `#00e5ff`)
      const primaryColor = isDual && viewMode === 'overlay' ? 0x00e5ff : 0x38bdf8;
      const primarySphere = isDual && viewMode === 'overlay' ? 0x0284c7 : 0x0ea5e9;
      const m1 = buildSkeletonModel(primaryBVH, primaryColor, primarySphere, offset1);

      group1Ref.current = m1.group;
      skeletonHelper1Ref.current = m1.helper;
      mixer1Ref.current = m1.mixer;
      action1Ref.current = m1.action;
      durationRef.current = m1.duration;
      totalFramesRef.current = m1.totalFrames;
      jointMeshesRef.current.push(...m1.meshes);

      scene.add(m1.group);

      // Secondary Skeleton if dual mode (Neon Violet `#c084fc` or Emerald `#10b981`)
      if (isDual && secondaryBVH) {
        const secColor = 0xc084fc;
        const secSphere = 0x9333ea;
        const m2 = buildSkeletonModel(secondaryBVH, secColor, secSphere, offset2);

        group2Ref.current = m2.group;
        skeletonHelper2Ref.current = m2.helper;
        mixer2Ref.current = m2.mixer;
        action2Ref.current = m2.action;
        jointMeshesRef.current.push(...m2.meshes);

        scene.add(m2.group);

        // Synchronize playback timeline
        if (action1Ref.current && action2Ref.current) {
          action2Ref.current.time = action1Ref.current.time;
        }
      }

      if (action1Ref.current) action1Ref.current.paused = !isPlayingRef.current;
      if (action2Ref.current) action2Ref.current.paused = !isPlayingRef.current;
    } catch (err) {
      console.error('Failed to parse and render BVH:', err);
    }
  }, [primaryBVH, secondaryBVH, viewMode]);

  // Imperative Methods
  useImperativeHandle(ref, () => ({
    play: () => {
      isPlayingRef.current = true;
      setIsPlaying(true);
      if (action1Ref.current) action1Ref.current.paused = false;
      if (action2Ref.current) action2Ref.current.paused = false;
    },
    pause: () => {
      isPlayingRef.current = false;
      setIsPlaying(false);
      if (action1Ref.current) action1Ref.current.paused = true;
      if (action2Ref.current) action2Ref.current.paused = true;
    },
    seek: (normalizedTime: number) => {
      const targetTime = normalizedTime * durationRef.current;
      if (action1Ref.current) {
        action1Ref.current.time = targetTime;
        if (mixer1Ref.current) mixer1Ref.current.update(0);
      }
      if (action2Ref.current) {
        action2Ref.current.time = targetTime;
        if (mixer2Ref.current) mixer2Ref.current.update(0);
      }
    },
    seekFrame: (frame: number) => {
      if (totalFramesRef.current <= 0) return;
      const normalizedTime = Math.max(0, Math.min(1, frame / totalFramesRef.current));
      const targetTime = normalizedTime * durationRef.current;
      if (action1Ref.current) {
        action1Ref.current.time = targetTime;
        if (mixer1Ref.current) mixer1Ref.current.update(0);
      }
      if (action2Ref.current) {
        action2Ref.current.time = targetTime;
        if (mixer2Ref.current) mixer2Ref.current.update(0);
      }
    },
    setSpeed: (speed: number) => {
      playbackSpeedRef.current = speed;
      if (mixer1Ref.current) mixer1Ref.current.timeScale = speed;
      if (mixer2Ref.current) mixer2Ref.current.timeScale = speed;
    },
    setCameraPreset: (preset: CameraPreset) => {
      if (!cameraRef.current || !controlsRef.current) return;
      const cam = cameraRef.current;
      const ctrl = controlsRef.current;
      if (preset === 'front') {
        cam.position.set(0, 45, 230);
        ctrl.target.set(0, 42, 0);
      } else if (preset === 'side') {
        cam.position.set(230, 45, 0);
        ctrl.target.set(0, 42, 0);
      } else if (preset === 'top') {
        cam.position.set(0, 260, 1);
        ctrl.target.set(0, 0, 0);
      } else {
        cam.position.set(0, 85, 230);
        ctrl.target.set(0, 42, 0);
      }
    },
    toggleGrid: () => {
      if (gridRef.current) {
        gridRef.current.visible = !gridRef.current.visible;
        setShowGrid(gridRef.current.visible);
      }
    },
    toggleTrails: () => {},
    resetCamera: () => {
      if (!cameraRef.current || !controlsRef.current) return;
      cameraRef.current.position.set(0, 85, 230);
      controlsRef.current.target.set(0, 42, 0);
    },
    fitToSkeleton: () => {
      if (!skeletonHelper1Ref.current || !cameraRef.current || !controlsRef.current) return;
      const bbox = new THREE.Box3();
      const bones = (skeletonHelper1Ref.current as any).skeleton?.bones || [];
      bones.forEach((bone: THREE.Bone) => {
        const wp = new THREE.Vector3();
        bone.getWorldPosition(wp);
        bbox.expandByPoint(wp);
      });
      if (skeletonHelper2Ref.current) {
        const bones2 = (skeletonHelper2Ref.current as any).skeleton?.bones || [];
        bones2.forEach((bone: THREE.Bone) => {
          const wp = new THREE.Vector3();
          bone.getWorldPosition(wp);
          bbox.expandByPoint(wp);
        });
      }
      const center = new THREE.Vector3();
      bbox.getCenter(center);
      const size = new THREE.Vector3();
      bbox.getSize(size);
      const maxDim = Math.max(size.x, size.y, size.z, 45);
      const fov = cameraRef.current.fov * (Math.PI / 180);
      let dist = Math.abs(maxDim / Math.sin(fov / 2)) * 0.72;
      dist = Math.max(50, Math.min(dist, 500));
      cameraRef.current.position.set(center.x, center.y + size.y * 0.15, center.z + dist);
      controlsRef.current.target.copy(center);
    },
  }));

  return (
    <div className="relative w-full h-full select-none overflow-hidden" style={{ backgroundColor: 'var(--viewport-bg)' }}>
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Empty State when no BVH is loaded */}
      {!primaryBVH && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center backdrop-blur-sm z-10 p-6 text-center"
          style={{ backgroundColor: 'var(--bg-page)', opacity: 0.97 }}
        >
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center mb-3 border"
            style={{ backgroundColor: 'var(--accent-bg)', borderColor: 'var(--accent-border)', color: 'var(--accent-text)' }}
          >
            <Eye className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold mb-1" style={{ color: 'var(--text-primary)' }}>No Motion Sequence Loaded</h3>
          <p className="text-xs max-w-sm mb-4" style={{ color: 'var(--text-muted)' }}>
            Select a trial from the Motion Lab or execute a task workbench to stream and animate 3D skeletal data.
          </p>
          {onLoadSample && (
            <button
              onClick={onLoadSample}
              className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs flex items-center gap-1.5 transition-colors shadow-sm shadow-cyan-600/30"
            >
              <Play className="w-3.5 h-3.5 fill-current" /> Load Default Trial (MF001)
            </button>
          )}
        </div>
      )}

      {/* Floating 3D Legend Badges for Dual Viewport */}
      {secondaryBVH && viewMode === 'side-by-side' && (
        <>
          <div
            className="absolute top-3.5 left-4 pointer-events-none backdrop-blur-md px-3 py-1.5 rounded-lg border flex items-center gap-2 shadow-lg"
            style={{ backgroundColor: 'var(--bg-header)', borderColor: 'var(--accent-border)' }}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[11px] font-semibold tracking-wide font-mono" style={{ color: 'var(--accent-text)' }}>
              {primaryLabel}
            </span>
          </div>
          <div
            className="absolute top-3.5 right-4 pointer-events-none backdrop-blur-md px-3 py-1.5 rounded-lg border border-purple-500/30 flex items-center gap-2 shadow-lg"
            style={{ backgroundColor: 'var(--bg-header)' }}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
            <span className="text-[11px] font-semibold text-purple-300 tracking-wide font-mono">
              {secondaryLabel}
            </span>
          </div>
        </>
      )}

      {secondaryBVH && viewMode === 'overlay' && (
        <div
          className="absolute top-3.5 left-4 pointer-events-none backdrop-blur-md px-3 py-1.5 rounded-lg border flex items-center gap-3 shadow-lg"
          style={{ backgroundColor: 'var(--bg-header)', borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span className="text-[11px] font-medium font-mono" style={{ color: 'var(--accent-text)' }}>{primaryLabel}</span>
          </div>
          <span className="font-mono text-xs" style={{ color: 'var(--border-strong)' }}>/</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-400" />
            <span className="text-[11px] font-medium text-purple-300 font-mono">{secondaryLabel}</span>
          </div>
        </div>
      )}

      {/* Hovered Joint Inspection HUD */}
      {hoveredJointInfo && (
        <div
          className="absolute top-3.5 right-4 pointer-events-none backdrop-blur-md px-3 py-2 rounded-lg border text-xs font-mono shadow-xl z-20 flex flex-col gap-1 min-w-[180px]"
          style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--accent-border)' }}
        >
          <div className="flex items-center justify-between border-b pb-1" style={{ borderColor: 'var(--border-subtle)' }}>
            <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Joint</span>
            <span className="font-bold" style={{ color: 'var(--accent-text)' }}>{hoveredJointInfo.name}</span>
          </div>
          <div className="flex justify-between text-[10px]" style={{ color: 'var(--text-muted)' }}>
            <span>Parent:</span>
            <span style={{ color: 'var(--text-secondary)' }}>{hoveredJointInfo.parentName}</span>
          </div>
          <div className="flex justify-between text-[10px]" style={{ color: 'var(--text-muted)' }}>
            <span>World Pos:</span>
            <span className="text-emerald-400">
              [{hoveredJointInfo.pos[0]}, {hoveredJointInfo.pos[1]}, {hoveredJointInfo.pos[2]}]
            </span>
          </div>
        </div>
      )}

      {/* Viewport Technical Status Pill */}
      <div
        className="absolute bottom-2.5 left-3.5 pointer-events-none flex items-center gap-2.5 text-[10px] backdrop-blur-md px-2.5 py-1 rounded-md border font-mono"
        style={{ backgroundColor: 'var(--bg-header)', borderColor: 'var(--border-subtle)', color: 'var(--text-muted)' }}
      >
        <span className="font-semibold" style={{ color: 'var(--accent-text)' }}>120.0 FPS</span>
        <span style={{ color: 'var(--border-strong)' }}>|</span>
        <span>31 Canonical Joints</span>
        <span style={{ color: 'var(--border-strong)' }}>|</span>
        <span className="uppercase font-bold" style={{ color: 'var(--text-secondary)' }}>{viewMode}</span>
      </div>
    </div>
  );
});

ThreeViewer.displayName = 'ThreeViewer';
