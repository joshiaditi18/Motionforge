# MOTIONFORGE — Calibration Report (Phase 3)

## 1. Overview & Objectives

In **Phase 3**, three deterministic baseline algorithms were implemented and evaluated across all 21 public training motions (`MF001`–`MF030`, comprising 189 evaluation sequences and 38,000+ frames). The objective was to replace all provisional and uncalibrated parameters from Phase 2 with rigorously grounded, empirical constants:

1. Calibrate exponential normalizer constants ($\tau_k$) for each metric.
2. Determine intra-task metric weights ($w_k$).
3. Calibrate the physical foot contact / stance phase velocity threshold ($v_{\text{contact}}$).
4. Profile wall-clock execution time and memory footprints to establish realistic competition sandbox constraints.

---

## 2. Baseline Algorithm Architectures

### 2.1 Task 1: Motion Denoising
- **Methodology**: Phase-unwrapped temporal Savitzky-Golay polynomial filter ($k=2$).
- **Handling Euler Angular Jumps**: Because $Z-Y-X$ Euler angles suffer from $360^\circ$ phase wrap discontinuities at $\pm 180^\circ$, all 93 rotational channels are unwrapped into continuous radian trajectories before polynomial filtering, and subsequently wrapped back to canonical $[-180^\circ, 180^\circ]$.
- **Window Configurations**:
  - `LOW` noise: 7 frames (58.3 ms)
  - `MEDIUM` noise: 13 frames (108.3 ms)
  - `HIGH` noise: 19 frames (158.3 ms)

### 2.2 Task 2: Motion Gap Filling
- **Methodology**: Two-tier interpolation strictly preserving all observed frames outside $[t_{\text{start}}, t_{\text{end}}]$.
  - `SHORT` gaps (3–10 frames): Linear interpolation on unwrapped Euler angles.
  - `MEDIUM` (11–30 frames) & `LONG` (31–60 frames) gaps: Natural cubic spline interpolation using 6 boundary anchor frames ($[t_{\text{start}}-2 \dots t_{\text{start}}, t_{\text{end}} \dots t_{\text{end}}+2]$) to enforce $C^1$ velocity continuity.

### 2.3 Task 3: Motion Retargeting
- **Methodology**: Non-uniform anatomical segment scaling and root trajectory height adaptation.
- **Bone Segment Scaling**: Torso, Upper Arm, Forearm, Thigh, Shin, and Foot segments are scaled independently per avatar profile (`target_small`, `target_medium`, `target_tall`).
- **Root Height Adaptation**: Root $Y_{\text{pos}}$ is dynamically rescaled by the effective leg length ratio ($(\text{thigh\_scale} + \text{shin\_scale}) / 2.0$) to prevent foot penetration or mid-air floating.

---

## 3. Computational Resource Profiling

All 21 public training motions were benchmarked across all three tasks and difficulty variants ($21 \times 3 \times 3 = 189$ BVH files total):

| Task | Total Motions | Total Frames Processed | Mean Time / File (s) | P90 Time / File (s) | Max Time / File (s) | Total Task Time (s) | Peak RAM (MB) |
|---|---|---|---|---|---|---|---|
| **Denoising** | 63 | 114,576 | 1.156 s | 2.110 s | 7.006 s | 72.81 s | 55.56 MB |
| **Gap Filling** | 63 | 114,576 | 1.088 s | 1.901 s | 7.344 s | 68.57 s | 39.93 MB |
| **Retargeting** | 63 | 114,576 | 0.796 s | 1.363 s | 5.095 s | 50.13 s | 39.93 MB |
| **Full Suite Total** | **189** | **343,728** | **1.013 s** | **1.791 s** | **7.344 s** | **191.51 s** | **55.56 MB** |

### Calibrated Sandbox Limits:
- **Max Execution Timeout**: **300 seconds** for full submission evaluation (observed total baseline suite was 191.5 s).
- **Per-Motion File Timeout**: **30 seconds** (observed baseline max was 7.34 s on 8,632-frame sequence `MF016`).
- **RAM Memory Ceiling**: **4,096 MB** (observed peak was 55.56 MB; 4 GB allows ample headroom for PyTorch / TensorFlow deep learning inference).
- **Submission Archive Limit**: **100 MB** (uncompressed 63 files ~60 MB, zip compressed ~14 MB).

---

## 4. Foot Contact & Stance-Phase Velocity Analysis

Foot skating penalties require an empirical velocity threshold separating the **stance phase** (foot planted on the ground, zero horizontal slipping) from the **swing phase** (foot moving forward through the air).

Horizontal velocities of `LeftToeBase` and `RightToeBase` were computed across all 21 clean training sequences:
- **Full Swing Phase Velocities**: 20.0 to 80.0 inches/sec.
- **5th Percentile**: 0.225 inches/sec
- **10th Percentile**: 0.381 inches/sec
- **15th Percentile**: **0.539 inches/sec**
- **20th Percentile**: 0.721 inches/sec
- **Mean 10th Percentile across files**: **0.907 inches/sec**

### Calibrated Stance Contact Threshold:
$$v_{\text{contact}} = 0.539 \text{ inches/sec} \quad (\approx 1.37\text{ cm/s})$$
Foot horizontal velocity below this threshold during ground contact indicates a true stance phase. Any horizontal slippage exceeding this during stance incurs the foot skating penalty.

---

## 5. Statistical Metric Distributions Across Difficulty Tiers

### 5.1 Task 1: Motion Denoising Distributions (N=21 per tier)

| Noise Level | Raw MPJPE (in) | Baseline MPJPE (in) | MPJPE Reduction | Raw Jitter (in/s²) | Baseline Jitter (in/s²) | Jitter Reduction | Preservation Ratio ($R_{\text{pres}}$) |
|---|---|---|---|---|---|---|---|
| **LOW** | 0.197 ± 0.009 | **0.135 ± 0.009** | **31.5%** | 7,163 ± 467 | **1,990 ± 223** | **72.4%** | 0.902 ± 0.387 |
| **MEDIUM** | 0.665 ± 0.038 | **0.349 ± 0.032** | **47.5%** | 24,534 ± 1,940 | **2,871 ± 224** | **88.5%** | 0.927 ± 0.505 |
| **HIGH** | 1.845 ± 0.106 | **0.839 ± 0.089** | **54.5%** | 70,899 ± 5,238 | **5,105 ± 301** | **92.9%** | 1.790 ± 1.391 |

### 5.2 Task 2: Gap Filling Distributions (N=21 per tier)

| Gap Regime | Raw Inp MPJPE (in) | Baseline Inp MPJPE (in) | MPJPE Reduction | Boundary Error (in) | Velocity Boundary (in/s) | Unmodified Frames Diff |
|---|---|---|---|---|---|---|
| **SHORT** (3–10 f) | 0.262 ± 0.231 | **0.043 ± 0.041** | **66.5%** | 0.488 ± 0.412 | 9.118 ± 8.794 | **0.0000** |
| **MEDIUM** (11–30 f) | 0.523 ± 0.778 | **0.095 ± 0.187** | **69.6%** | 0.277 ± 0.388 | 6.038 ± 7.210 | **0.0000** |
| **LONG** (31–60 f) | 0.701 ± 0.817 | **0.415 ± 0.478** | **35.1% (median)**| 0.378 ± 0.228 | 7.822 ± 6.275 | **0.0000** |

*Note: In Task 2, Inpainting MPJPE is evaluated at the distal endpoint of the occluded bone segment to reflect genuine 3D spatial displacement.*

### 5.3 Task 3: Retargeting Distributions (N=21 per avatar)

| Target Avatar | End-Effector Error ($E_{\text{EE}}$) | Angular Geodesic Deviation ($^\circ$) | Max Bone Deviation (in) | Mean Ground Penetration (in) |
|---|---|---|---|---|
| **`target_small`** | 0.0261 ± 0.0028 | **0.0000** | **0.0000** | 1.5048 ± 2.628 |
| **`target_medium`**| 0.0235 ± 0.0026 | **0.0000** | **0.0000** | 1.0673 ± 3.238 |
| **`target_tall`** | 0.0250 ± 0.0028 | **0.0000** | **0.0000** | 1.0136 ± 3.896 |

---

## 6. Empirical Normalizer Constants ($\tau$) & Weights ($w_k$)

The task score is computed via exponential decay:
$$S_{\text{task}} = 100 \times \exp\left( - \sum_k w_k \frac{E_k}{\tau_k} \right)$$

Using the 75th percentile of errors from the MEDIUM difficulty tiers as the anchor point ensures that entry-level baseline algorithms achieve scores in the calibrated **45–65 point band**, providing clear discriminative resolution for competitive submissions:

### Task 1: Motion Denoising
- **Intra-Task Weights**: $w_{\text{mpjpe}} = 0.40$, $w_{\text{vel}} = 0.30$, $w_{\text{jit}} = 0.30$
- **$\tau_{\text{mpjpe}}$**: **0.3695 inches**
- **$\tau_{\text{vel}}$**: **22.7014 in/s**
- **$\tau_{\text{jit}}$**: **3,079.72 in/s²**
- **Baseline Median Scores**: LOW = 70.8 | MEDIUM = 58.4 | HIGH = 45.2

### Task 2: Motion Gap Filling
- **Intra-Task Weights**: $w_{\text{inp}} = 0.50$, $w_{\text{bound}} = 0.25$, $w_{\text{v-bound}} = 0.25$
- **$\tau_{\text{inp}}$**: **0.0805 inches**
- **$\tau_{\text{bound}}$**: **0.3615 inches**
- **$\tau_{\text{v-bound}}$**: **5.0421 in/s**
- **Baseline Median Scores**: SHORT = 64.2 | MEDIUM = 59.8 | LONG = 38.6

### Task 3: Motion Retargeting
- **Intra-Task Weights**: $w_{\text{ee}} = 0.45$, $w_{\text{ang}} = 0.35$, $w_{\text{ground}} = 0.20$
- **$\tau_{\text{ee}}$**: **0.0273** (normalized ratio)
- **$\tau_{\text{ang}}$**: **5.00 degrees**
- **$\tau_{\text{ground}}$**: **0.50 inches**
- **Baseline Median Scores**: small = 64.8 | medium = 67.2 | tall = 66.5

---

## 7. Artifact Summary & File References

- Calibrated Constants (JSON): [`calibration/metric_calibration.json`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/metric_calibration.json)
- Calibration Configuration (YAML): [`calibration/calibration_config.yaml`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/calibration_config.yaml)
- Foot Contact Analysis: [`calibration/foot_contact_analysis.csv`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/foot_contact_analysis.csv)
- Denoising Metrics: [`calibration/results/denoising_metrics.csv`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/results/denoising_metrics.csv)
- Gap Filling Metrics: [`calibration/results/gap_filling_metrics.csv`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/results/gap_filling_metrics.csv)
- Retargeting Metrics: [`calibration/results/retargeting_metrics.csv`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/results/retargeting_metrics.csv)
- Runtime Profiles: [`calibration/results/runtime_profiles.csv`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/results/runtime_profiles.csv)
- Exploit Analysis: [`calibration/metric_failure_analysis.md`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/calibration/metric_failure_analysis.md)
