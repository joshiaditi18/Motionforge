# MOTIONFORGE — Dataset Statistics Report

## Executive Summary

The **MOTIONFORGE: Clean. Complete. Retarget.** benchmark dataset is built upon verified motion captures from the official **Carnegie Mellon University (CMU) Motion Capture Database** standardized into unified **Biovision Hierarchy (BVH)** representations.

---

## Dataset Scale & Metrics

| Metric | Value | Description |
|---|---|---|
| **Total Base Motions** | **30** | Standardized ground-truth capture sequences |
| **Total Frames** | **54,560** | High-fidelity optical mocap frames |
| **Average Sampling Rate** | **120.0 FPS** | Professional capture frame rate |
| **Average Sequence Duration** | **15.156s** | Mean duration per motion trial |
| **Shortest Sequence** | **1.2s** | e.g. Sprint / run bursts |
| **Longest Sequence** | **82.833s** | e.g. Complex agility, dance, and multi-action trials |
| **Standardized Skeleton Joints** | **31** | 31 functional anatomical joints + 7 End Sites |
| **Total Degrees of Freedom** | **96 channels** | 6-DOF Root + 3-DOF Euler rotations per bone |
| **Total Competition Files** | **300 files** | 30 Clean Ground Truth + 270 Public Challenge files |

---

## Task Distribution

| Task Challenge | Files Generated | Configurations & Parameters |
|---|---|---|
| **Task 1: Denoising** | **90 files** | **LOW**, **MEDIUM**, **HIGH** realistic optical sensor jitter & glitch |
| **Task 2: Gap Filling** | **90 files** | **SHORT** (3–10f), **MEDIUM** (11–30f), **LONG** (31–60f) tracking loss occlusions |
| **Task 3: Retargeting** | **90 files** | **target_small**, **target_medium**, **target_tall** bone proportion adaptations |
| **Ground Truth (Hidden)** | **30 files** | Kept in isolated evaluation vault (`hidden/ground_truth/`) |

---

## Motion Diversity Matrix

The 30 motion sequences cover diverse locomotion and full-body athletic dynamics:
- **Locomotion**: Standard walk, slow walk, exaggerated stride, sprint/run, jog-through, veer turns, walking to running transition.
- **Dynamic Jumps & Acrobatics**: Vertical high jump, forward leap, 180-degree turnaround jump, cartwheels.
- **Rhythmic & Dance**: Authentic salsa partner dance sequences, Charleston dance steps.
- **Martial Arts & Combat**: Multi-strike punch combinations, kicking, stretch-and-evasion drills.
- **Complex Recovery**: Getting up from the ground lying flat on the back, navigating around obstacles.
