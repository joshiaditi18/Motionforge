# MOTIONFORGE — Baseline Gap Filling Algorithm

## Approach
This baseline performs inpainting over occluded joint intervals while strictly preserving all surrounding observed frames.
- **Short Gaps (3–10 frames)**: Linear interpolation on unwrapped Euler angles.
- **Medium & Long Gaps (11–60 frames)**: Natural Cubic Spline interpolation using boundary velocity anchors to ensure $C^1$ velocity continuity at transition edges.
- **Observed Frames Conservation**: Every frame outside $[t_{\text{start}}, t_{\text{end}}]$ is copied bit-for-bit with zero modification.

## Usage
```bash
python baseline_gap_filling.py --input <gapped.bvh> --output <filled.bvh> --method <linear|cubic>
```
