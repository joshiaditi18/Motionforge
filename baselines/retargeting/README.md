# MOTIONFORGE — Baseline Motion Retargeting Algorithm

## Approach
This baseline performs **proportional skeletal bone retargeting and root height adjustment** to map clean source motions onto disparate target avatar morphologies (`target_small`, `target_medium`, `target_tall`).

- **Hierarchical Bone Scaling**: Scales rest bone offsets across anatomical segments:
  - Torso (`LowerBack`, `Spine`, `Spine1`, `Neck`, `Neck1`, `Head`)
  - Upper Arms (`LeftShoulder`, `RightShoulder`, `LeftArm`, `RightArm`)
  - Forearms (`LeftForeArm`, `RightForeArm`)
  - Thighs (`LeftUpLeg`, `RightUpLeg`)
  - Shins (`LeftLeg`, `RightLeg`)
  - Feet & Toes (`LeftFoot`, `RightFoot`, `LeftToeBase`, `RightToeBase`)
- **Root Trajectory Adaptation**: Root vertical position ($Y$-translation) is scaled proportionally to leg length changes ($(\text{thigh\_scale} + \text{shin\_scale}) / 2.0$) to avoid foot-penetration into the ground or mid-air floating.
- **Topology & Orientation Invariance**: Preserves the exact canonical 31-joint hierarchy, channel count (96), and local joint rotational coordinate frames.

## Usage
```bash
python baseline_retargeting.py --source <clean.bvh> --output <retargeted.bvh> --target <target_small|target_medium|target_tall>
```
