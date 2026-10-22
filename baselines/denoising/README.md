# MOTIONFORGE — Baseline Denoising Algorithm

## Approach
This baseline applies a **phase-unwrapped Savitzky-Golay polynomial filter** to temporal channels.
- **Root Translation**: Smoothed using local polynomial fitting.
- **Joint Rotations**: To prevent wrap-around jumps at $\pm 180^\circ$ boundaries, Euler angles are unwrapped into continuous trajectories before filtering, then wrapped back to canonical range $[-180^\circ, 180^\circ]$.
- **Window Lengths**:
  - `LOW`: 7 frames (~58 ms)
  - `MEDIUM`: 13 frames (~108 ms)
  - `HIGH`: 19 frames (~158 ms)

## Usage
```bash
python baseline_denoising.py --input <noisy.bvh> --output <denoised.bvh> --level <LOW|MEDIUM|HIGH>
```
