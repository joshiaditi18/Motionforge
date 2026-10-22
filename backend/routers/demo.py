"""
Demo Router — provides structured metadata for the Phase 12 interactive demo.
All processing still goes through the existing task endpoints.
This endpoint only supplies task descriptions, metric explanations, and
recommended demo motions for the guided demo wizard.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["Demo"])


TASK_DESCRIPTIONS = {
    "denoising": {
        "id": "denoising",
        "title": "Task 1: Motion Denoising",
        "weight": 0.30,
        "problem": (
            "Optical motion-capture markers frequently pick up high-frequency sensor noise — "
            "small, rapid position fluctuations caused by marker occlusion, reflections, and "
            "measurement uncertainty. This jitter distorts joint trajectories without altering "
            "the underlying movement intent."
        ),
        "approach": (
            "MOTIONFORGE applies a phase-unwrapped Savitzky–Golay polynomial filter (polyorder=2) "
            "across all 96 rotation channels simultaneously. Phase unwrapping prevents artefacts "
            "at gimbal-lock boundaries before smoothing and restores correct rotation sign after. "
            "Window length is calibrated per noise severity: 7 frames (LOW), 13 frames (MEDIUM), "
            "19 frames (HIGH)."
        ),
        "parameters": [
            {"key": "noise_level", "label": "Noise Severity", "options": ["LOW", "MEDIUM", "HIGH"],
             "descriptions": {
                 "LOW": "σ = 0.5°. Mild sensor noise — motion trajectories are mostly intact.",
                 "MEDIUM": "σ = 1.5°. Moderate noise — visible jitter in fast segments.",
                 "HIGH": "σ = 4.0°. Severe corruption — trajectories substantially distorted."
             }
             }
        ],
        "output_metrics": [
            {"id": "mpjpe", "name": "MPJPE", "unit": "inches", "direction": "lower",
             "explanation": "Mean Per-Joint Position Error. Average Euclidean distance between predicted and ground-truth joint positions across all 31 joints and all frames. Measures how accurately joint locations are recovered."},
            {"id": "jitter_reduction_pct", "name": "Jitter Reduction", "unit": "%", "direction": "higher",
             "explanation": "Percentage reduction in second-order temporal acceleration error (in/s²). Higher is better — indicates how much high-frequency noise has been removed without over-smoothing."},
            {"id": "velocity_error", "name": "Velocity Error (JVE)", "unit": "in/s", "direction": "lower",
             "explanation": "First-order finite-difference velocity error. Measures whether the filter preserves the speed profile of each joint — over-smoothing raises this metric."},
            {"id": "motion_preservation", "name": "Kinetic Energy Ratio", "unit": "ratio", "direction": "neutral",
             "explanation": "Ratio of output velocity energy to input velocity energy. Values in [0.35, 3.00] confirm the algorithm did not collapse motion to near-zero or amplify it pathologically."},
        ],
        "recommended_motions": ["MF001", "MF002", "MF003"],
    },
    "gap_filling": {
        "id": "gap_filling",
        "title": "Task 2: Gap Filling (Inpainting)",
        "weight": 0.30,
        "problem": (
            "Marker occlusion — when a reflective marker is temporarily hidden from cameras — "
            "creates contiguous intervals of missing data called gaps. Gaps cannot simply be "
            "deleted; the surrounding motion must be reconstructed to maintain temporal continuity."
        ),
        "approach": (
            "MOTIONFORGE uses natural cubic spline interpolation across each missing rotation "
            "channel independently. The algorithm matches position and first derivative "
            "(velocity) at both boundaries to produce smooth, physically plausible "
            "reconstructions. Observed (non-gap) frames are strictly unchanged."
        ),
        "parameters": [
            {"key": "gap_type", "label": "Gap Difficulty", "options": ["SHORT", "MEDIUM", "LONG"],
             "descriptions": {
                 "SHORT": "5–15 frames (~0.04–0.12 s). Gaps during stable segments — simple interpolation suffices.",
                 "MEDIUM": "25–40 frames (~0.21–0.33 s). Gaps spanning motion transitions — boundary matching is critical.",
                 "LONG": "60–80 frames (~0.50–0.67 s). Gaps spanning complex dynamics — reconstruction degrades gracefully."
             }
             }
        ],
        "output_metrics": [
            {"id": "inpainting_mpjpe", "name": "Inpainting Error (MPJPE)", "unit": "inches", "direction": "lower",
             "explanation": "Mean Per-Joint Position Error computed only inside the gap interval. Measures how well missing frames were reconstructed relative to clean ground truth."},
            {"id": "boundary_error", "name": "Boundary Position Error", "unit": "inches", "direction": "lower",
             "explanation": "Position error at the first and last reconstructed frame. Low values indicate seamless join between observed and reconstructed segments."},
            {"id": "velocity_boundary_error", "name": "Boundary Velocity Error", "unit": "in/s", "direction": "lower",
             "explanation": "Velocity (first derivative) discontinuity at gap boundaries. Ideally near zero — sudden velocity jumps produce visually jarring artefacts."},
            {"id": "unmodified_max_diff", "name": "Observed Frame Invariance", "unit": "inches", "direction": "lower",
             "explanation": "Maximum absolute change to any observed (non-gap) frame. Must be < 1×10⁻⁵ in — the algorithm must not alter frames it was not asked to fill."},
        ],
        "recommended_motions": ["MF001", "MF002", "MF003"],
    },
    "retargeting": {
        "id": "retargeting",
        "title": "Task 3: Cross-Morphology Retargeting",
        "weight": 0.40,
        "problem": (
            "Motion captured from one performer cannot directly drive avatars with different body "
            "proportions — limb lengths, torso ratios, and foot sizes differ. Naively copying "
            "joint rotations causes foot sliding, ground penetration, and proportion-distorted poses."
        ),
        "approach": (
            "MOTIONFORGE applies per-segment bone-length scaling to the source skeleton, "
            "preserving joint rotation values while adjusting the physical reach of each limb. "
            "A contact-aware post-pass clamps foot joint world Y coordinates to ≥ 0 to prevent "
            "ground penetration, using FK forward kinematics on each frame."
        ),
        "parameters": [
            {"key": "target_type", "label": "Target Avatar", "options": ["target_small", "target_medium", "target_tall"],
             "descriptions": {
                 "target_small": "Compact stature (0.78× height scale). Shorter limbs and reduced torso.",
                 "target_medium": "Athletic stature (1.08× height scale). Slightly longer limbs and wider torso.",
                 "target_tall": "Elongated stature (1.30× height scale). Long limbs, extended torso and femur."
             }
             }
        ],
        "output_metrics": [
            {"id": "end_effector_error", "name": "End-Effector Error", "unit": "inches", "direction": "lower",
             "explanation": "Mean position error at wrist and ankle joints — the chain endpoints most sensitive to bone-length scaling errors. Captures whether hand/foot trajectories match ground-truth retargeted positions."},
            {"id": "bone_length_violation_max", "name": "Bone Length Violation", "unit": "inches", "direction": "lower",
             "explanation": "Maximum deviation of any output bone length from its target specification. Bone lengths must be within 1×10⁻⁵ in of the target — larger violations indicate structural inconsistency."},
            {"id": "ground_penetration_penalty", "name": "Ground Penetration", "unit": "inches", "direction": "lower",
             "explanation": "Mean depth of foot joints below the ground plane (Y = 0). Ideally 0.0 — ground penetration indicates the contact-aware post-pass did not fully correct foot placement."},
            {"id": "temporal_velocity_ratio", "name": "Temporal Smoothness Ratio", "unit": "ratio", "direction": "neutral",
             "explanation": "Ratio of output joint velocity magnitude to source velocity. Values near 1.0 indicate the retargeted motion preserves the temporal dynamics of the source performance."},
        ],
        "recommended_motions": ["MF001", "MF002", "MF003"],
    }
}

METRIC_GLOSSARY = {
    "mpjpe": {
        "name": "MPJPE — Mean Per-Joint Position Error",
        "unit": "inches",
        "direction": "lower is better",
        "plain_english": (
            "Imagine placing a ruler between the predicted joint position and the "
            "true joint position, for every joint in every frame, then averaging all those "
            "distances. Lower MPJPE means the algorithm kept joint locations closer to ground truth."
        ),
        "context": "The canonical reconstruction accuracy metric in human motion research.",
    },
    "jitter": {
        "name": "Temporal Jitter (Acceleration Error)",
        "unit": "in/s²",
        "direction": "lower is better",
        "plain_english": (
            "Second-order temporal differences capture how rapidly joint velocities change. "
            "Sensor noise manifests as very high-frequency jitter — acceleration values "
            "far larger than human biomechanics produce. Lower values mean smoother trajectories."
        ),
        "context": "Used alongside MPJPE to confirm noise removal without over-smoothing.",
    },
    "inpainting_error": {
        "name": "Inpainting MPJPE (Gap Reconstruction Error)",
        "unit": "inches",
        "direction": "lower is better",
        "plain_english": (
            "Same as MPJPE but computed only inside the missing-frame interval. "
            "Measures how well the algorithm reconstructed frames it never observed."
        ),
        "context": "Lower values mean the gap was filled closer to what a real performer would have done.",
    },
    "boundary_error": {
        "name": "Boundary Position Continuity Error",
        "unit": "inches",
        "direction": "lower is better",
        "plain_english": (
            "Measures the position jump at the edges where observed and reconstructed frames meet. "
            "A low boundary error means the seam is invisible — observed frames connect smoothly."
        ),
        "context": "Critical for visual quality; large boundary errors produce visible pops.",
    },
    "end_effector_error": {
        "name": "End-Effector Position Error",
        "unit": "inches",
        "direction": "lower is better",
        "plain_english": (
            "The position error specifically at wrist and ankle joints — the tips of the kinematic "
            "chains. These are the joints most sensitive to bone-length scaling errors because "
            "small angle errors compound across the full chain length."
        ),
        "context": "A retargeted motion can look anatomically wrong even when average MPJPE is acceptable.",
    },
    "bone_length_violation": {
        "name": "Bone Length Structural Violation",
        "unit": "inches",
        "direction": "lower is better (must be < 1e-5)",
        "plain_english": (
            "Measures whether the output skeleton actually has the bone lengths it was supposed to. "
            "The constraint is strict: bones must match the target specification within 0.00001 inches. "
            "Any larger deviation indicates the retargeting computation has a structural error."
        ),
        "context": "Validated by the Phase 5 schema validator before scoring proceeds.",
    },
    "noise_level": {
        "name": "Gaussian Noise Severity",
        "unit": "standard deviation in degrees",
        "direction": "n/a — configuration parameter",
        "plain_english": (
            "Synthetic Gaussian noise is added to clean joint rotations to simulate real marker noise. "
            "LOW (σ=0.5°): barely perceptible. MEDIUM (σ=1.5°): visibly noisy fast segments. "
            "HIGH (σ=4.0°): severely distorted trajectories."
        ),
        "context": "The three levels correspond to the three competition sub-tasks for denoising.",
    },
    "gap_type": {
        "name": "Gap Difficulty Category",
        "unit": "frames",
        "direction": "n/a — configuration parameter",
        "plain_english": (
            "SHORT gaps (5–15 frames) occur during stable, slow segments — easy to interpolate. "
            "MEDIUM gaps (25–40 frames) cross motion transitions — boundary velocity matching matters. "
            "LONG gaps (60–80 frames) span complex actions — reconstruction degrades toward the center."
        ),
        "context": "Each motion has one pre-defined gap of each category, placed at scientifically selected locations.",
    },
}


@router.get("/tasks")
def get_task_descriptions():
    """Returns structured descriptions of each processing task for the guided demo."""
    return TASK_DESCRIPTIONS


@router.get("/glossary")
def get_metric_glossary():
    """Returns plain-English explanations for all key metrics and configuration parameters."""
    return METRIC_GLOSSARY


@router.get("/recommended_motions")
def get_recommended_motions():
    """Returns a list of motion IDs recommended for demonstration purposes."""
    return {
        "motions": ["MF001", "MF002", "MF003"],
        "reason": "These motions cover walking, running, and jump actions — representative of the full dataset diversity."
    }
