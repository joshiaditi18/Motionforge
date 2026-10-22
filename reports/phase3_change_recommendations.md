# MOTIONFORGE — Phase 3 Change Recommendations Report

## 1. Executive Summary & Purpose

During Phase 2, several configuration parameters in [`config/competition.yaml`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/config/competition.yaml) and sections of [`docs/COMPETITION_SPECIFICATION.md`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/docs/COMPETITION_SPECIFICATION.md) were marked with:
`NEEDS CALIBRATION IN PHASE 3/4`

In accordance with competition development protocol, **all Phase 2 specification documents remained strictly frozen during Phase 3**. This report formally documents the empirical findings from Phase 3 and provides concrete, ready-to-merge recommendations to finalize these parameters before implementing the Phase 4 evaluation engine.

---

## 2. Recommended Updates for `config/competition.yaml`

The following parameters in `config/competition.yaml` should be updated from `null` to their empirically calibrated values:

```yaml
scoring:
  provisional_weights:
    denoising: 0.30
    gap_filling: 0.30
    retargeting: 0.40
  normalization:
    method: "exponential_decay"
    # Calibrated from Phase 3 baseline runs across 21 public training motions
    mpjpe_tau: 0.3695                  # Replaces null (inches, P75 on Medium noise)
    velocity_tau: 22.7014              # Replaces null (in/s, P75 on Medium noise)
    jitter_tau: 3079.72                # Replaces null (in/s^2, P75 on Medium noise)
    inpainting_tau: 0.0805             # Replaces null (inches, P75 on Medium gaps)
    boundary_tau: 0.3615               # Replaces null (inches, P75 on Medium gaps)
    v_boundary_tau: 5.0421             # Replaces null (in/s, P75 on Medium gaps)
    end_effector_tau: 0.0273           # Replaces null (normalized limb ratio, P75)
    angular_tau: 5.0                   # Replaces null (degrees, geodesic threshold)
    ground_penetration_tau: 0.50       # Replaces null (inches floor tolerance)
    foot_contact_velocity_threshold: 0.539 # Replaces null (in/s, 15th percentile toe velocity)

runtime:
  # Calibrated from hardware profiling (observed max single-file 7.34s, peak RAM 55.6 MB)
  timeout_seconds: 300                 # Replaces null (provisional 300s finalized)
  single_file_timeout_seconds: 30      # New recommendation (guards against infinite loops)
  memory_limit_mb: 4096                # Replaces null (lowered from provisional 8192 MB)
  max_archive_size_mb: 100             # Replaces null (provisional 100 MB finalized)
  network_access: false                # Finalized
  sandboxed: true                      # Finalized

submission:
  max_daily_attempts: 5                # Replaces null (provisional 5 finalized)
  leaderboard_selection: "BEST"        # Finalized
```

---

## 3. Recommended Clarifications for `docs/COMPETITION_SPECIFICATION.md`

### 3.1 Task 2: Distal Joint Endpoint Evaluation
- **Issue**: In Forward Kinematics, rotating an internal non-root joint $j$ leaves the 3D position of joint pivot $\mathbf{p}_j$ unchanged relative to its parent. The rotation moves its **distal bone endpoint** ($j_{\text{distal}} = \text{node.children}[0]$ or terminal end site) and all downstream descendants.
- **Recommendation**: In Section 8.2 (Inpainting MPJPE), clarify that:
  $$E_{\text{inp}} = \frac{1}{t_{\text{end}} - t_{\text{start}} + 1} \sum_{t=t_{\text{start}}}^{t_{\text{end}}} \|\mathbf{p}_{t, j_{\text{distal}}}^{\text{pred}} - \mathbf{p}_{t, j_{\text{distal}}}^{\text{gt}}\|_2$$
  where $j_{\text{distal}}$ is the child endpoint of the occluded segment (e.g., `RightArm` $\rightarrow$ `RightForeArm`; `Head` $\rightarrow$ `Head End Site`).

### 3.2 Foot Skating Stance Velocity Threshold
- **Issue**: Foot skating penalty required a grounded threshold to detect stance phase.
- **Recommendation**: In Section 8.2, specify that stance contact is identified when horizontal toe velocity $v_{\text{toe}} < 0.539\text{ inches/sec}$ ($1.37\text{ cm/s}$), corresponding to the empirical 15th percentile across all training frames.

### 3.3 Anti-Degeneracy Guardrails
- **Issue**: Exploit testing revealed that submitting an all-zero or static rest pose frame eliminates jitter but produces zero motion dynamics.
- **Recommendation**: In Section 10, formalize an automated disqualification rule:
  $$\text{If } R_{\text{pres}} < 0.35 \text{ or } R_{\text{pres}} > 3.0 \implies \text{Score} = 0.0 \text{ (Degenerate)}$$

---

## 4. Phase 4 Implementation Readiness

With these recommendations documented:
1. The baseline algorithms provide clear benchmarks against which to test the Phase 4 evaluator.
2. The calibrated normalizers eliminate all arbitrary scoring constants.
3. The evaluation engine can be built in Phase 4 knowing exactly how each metric behaves on realistic mocap data.
