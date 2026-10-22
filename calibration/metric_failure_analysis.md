# MOTIONFORGE — Metric Failure & Exploit Analysis

## 1. Executive Summary & Purpose

A robust competitive benchmark must be immune to **metric gaming**, **shortcuts**, and **adversarial exploits**. If an evaluation suite relies on a single naive metric (e.g., only position error, or only acceleration smoothness), participants can achieve high leaderboard ranks through degenerative solutions (e.g., freezing the skeleton, global blurring, or identity copies) that fail entirely in visual or kinematic realism.

During **Phase 3**, we subjected the proposed metric formulation to systematic empirical adversarial testing against baseline motions to discover edge cases, loopholes, and failure modes.

---

## 2. Tested Adversarial Exploits & Empirical Results

We tested four primary adversarial submissions on motion `MF001` (Medium Optical Noise) alongside the calibrated Savitzky-Golay baseline:

| Submission Profile | MPJPE (inches) | JVE (in/s) | Jitter (in/s²) | Motion Preservation Ratio ($R_{\text{pres}}$) | Leaderboard Outcome |
|---|---|---|---|---|---|
| **Calibrated Baseline** | **0.3441** | **21.0164** | **2,824.32** | **0.5757** | **Pass (Score ~58.4)** |
| **Exploit A: Raw Corrupted Copy** | 0.6622 | 120.0350 | 25,624.94 | 11.8046 | **Failed (Score < 4.2)** |
| **Exploit B: Flatline Rest Pose** | 32.3204 | 26.6865 | 522.03 | 0.0000 | **Failed / Disqualified** |
| **Exploit C: Extreme Over-smoothing**| 1.2967 | 11.2578 | 581.36 | 0.2280 | **Failed (Score ~18.6)** |

---

## 3. Detailed Failure Mode Analysis

### Exploit A: The Identity / Pass-Through Shortcut
- **Mechanism**: The participant submits the raw corrupted file without running any denoising or gap filling algorithm, attempting to score high purely on position fidelity without smoothing.
- **Vulnerability Avoided**: While raw input retains roughly the coarse trajectory ($E_{\text{MPJPE}} = 0.6622\text{ in}$), optical mocap jitter produces an astronomical acceleration penalty ($E_{\text{jit}} = 25,624\text{ in/s}^2$) and velocity error ($E_{\text{vel}} = 120.04\text{ in/s}$).
- **Why It Fails**: Under the multi-metric exponential decay formula:
  $$S = 100 \times \exp\left( - \left[ 0.40 \frac{0.6622}{\tau_{\text{mpjpe}}} + 0.30 \frac{120.04}{\tau_{\text{vel}}} + 0.30 \frac{25624}{\tau_{\text{jit}}} \right] \right) < 4.2$$
  The submission receives a near-zero score, rendering the shortcut completely ineffective.

### Exploit B: The Flatline / Static Freeze Shortcut
- **Mechanism**: The participant outputs a static rest pose (repeating frame 0 across the entire file). Because velocities and accelerations are identically zero, the participant attempts to game the jitter penalty.
- **Empirical Failure**:
  1. The positional error explodes catastrophically ($E_{\text{MPJPE}} = 32.32\text{ in}$, over 90× baseline error).
  2. The Motion Preservation Ratio collapses to identically $R_{\text{pres}} = 0.0000$.
- **Countermeasure Invariant**: Any submission with $R_{\text{pres}} < 0.35$ or $E_{\text{MPJPE}} > 5.0\text{ in}$ is flagged as a degenerate static artifact and receives an automatic score of 0.0.

### Exploit C: Extreme Over-Smoothing (Dynamics Blurring)
- **Mechanism**: The participant applies an excessively wide temporal low-pass filter (e.g., 101-frame moving average or polynomial) to artificially crush jitter.
- **Empirical Failure**:
  1. Jitter drops significantly to $581\text{ in/s}^2$, but deliberate human motion dynamics (rapid turns, kicks, arm swings) are erased.
  2. MPJPE nearly quadruples ($1.2967\text{ in}$ vs $0.3441\text{ in}$ baseline).
  3. The preservation ratio collapses to $0.2280$ (over 77% of deliberate kinetic energy lost).
- **Why It Fails**: The trade-off is heavily penalized: the gain in jitter is drastically outweighed by the surge in positional distortion and the low preservation ratio penalty.

### Exploit D: Gap Filling Outside-Interval Bleeding
- **Mechanism**: When inpainting an occluded window $[t_{\text{start}}, t_{\text{end}}]$, an algorithm applies global filtering across the entire motion rather than local inpainting.
- **Vulnerability Avoided**: The validation engine strictly enforces the **Fidelity Invariant**:
  $$\max_{t \notin [t_{\text{start}}, t_{\text{end}}]} |\mathbf{p}_t^{\text{pred}} - \mathbf{p}_t^{\text{clean}}| = 0$$
  Any modification outside the designated gap interval triggers immediate validation rejection (`REJECTED_OBSERVED_FRAMES_MODIFIED`).

### Exploit E: Global Uniform Scaling in Retargeting
- **Mechanism**: Rather than adjusting non-uniform anatomical segments (e.g. thigh 0.78, shin 0.76, torso 0.82), a participant applies a single global scale factor ($S=0.80$) to all bone offsets and translations.
- **Vulnerability Avoided**: The evaluator checks bone offsets against target hierarchy definitions:
  $$E_{\text{bone}} = \max_j | L_j^{\text{pred}} - L_j^{\text{target}} |$$
  If $E_{\text{bone}} > 10^{-3}$, the submission is rejected for violating target avatar morphology.

---

## 4. Key Metric Vulnerabilities Discovered During Phase 3

### Discovery 1: Pivot vs. Distal Joint Kinematics
- In hierarchical forward kinematics, rotating joint $j$ leaves the position of joint pivot $j$ completely unchanged relative to its parent. The rotation displaces its **distal child bone endpoint** ($j_{\text{child}}$) and descendants.
- *Remedy*: In Task 2 (Gap Filling), Inpainting MPJPE must evaluate the distal endpoint of the occluded segment ($j_{\text{distal}} = \text{node.children}[0]$), not the pivot origin.

### Discovery 2: Natural MoCap Pauses vs. Occlusion Gaps
- In natural CMU mo-cap trials, actors frequently hold limbs steady (e.g. standing still during initial T-pose calibration or knee lock during stance phase), resulting in zero angular difference ($\Delta \theta = 0$).
- A naive gap detector searching purely for $\Delta \theta = 0$ triggers false positives on natural stationary frames (51/90 trials had stationary pauses).
- *Remedy*: Challenge gap metadata is explicitly provided in metadata (`gap_metadata.csv`), and evaluator verifies inpainting strictly over the ground-truth interval $[t_{\text{start}}, t_{\text{end}}]$.

---

## 5. Architectural Guardrails for Phase 4 Evaluation Engine

1. **Dual Validation Gates**: Structural BVH compliance (joint names, frame counts, frame time, non-modified frame masks) must execute *prior* to numerical metric calculation.
2. **Anti-Degeneracy Bounds**: Submissions with $R_{\text{pres}} < 0.35$ or $R_{\text{pres}} > 3.0$ trigger automated capping.
3. **Double Precision Forward Kinematics**: All metric calculations must use float64 $Z-Y-X$ Euler matrix composition to avoid numerical drift.
