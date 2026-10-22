import os
import sys
import csv
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANDOM_SEED = 2026

def split_dataset():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 6D: CREATE DETERMINISTIC TRAIN / TEST SPLIT")
    print("=" * 70)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    metadata_dir = os.path.join(workspace_root, "metadata")
    hidden_gt_dir = os.path.join(workspace_root, "hidden", "ground_truth")

    motion_ids = [f"MF{i:03d}" for i in range(1, 31)]
    total_count = len(motion_ids)

    # 70% training (21), 30% testing (9)
    rng = np.random.RandomState(RANDOM_SEED)
    shuffled = motion_ids.copy()
    rng.shuffle(shuffled)

    train_count = int(round(total_count * 0.70))
    train_set = set(shuffled[:train_count])
    test_set = set(shuffled[train_count:])

    records = []
    for mid in motion_ids:
        split = "TRAINING" if mid in train_set else "TESTING"
        gt_loc = os.path.relpath(os.path.join(hidden_gt_dir, f"{mid}_clean.bvh"), workspace_root)
        records.append({
            'motion_id': mid,
            'split': split,
            'denoising_available': 'YES' if split == 'TRAINING' else 'EVALUATION_ONLY',
            'gap_filling_available': 'YES' if split == 'TRAINING' else 'EVALUATION_ONLY',
            'retargeting_available': 'YES' if split == 'TRAINING' else 'EVALUATION_ONLY',
            'ground_truth_location': gt_loc
        })

    out_csv = os.path.join(metadata_dir, "dataset_split.csv")
    fieldnames = [
        'motion_id',
        'split',
        'denoising_available',
        'gap_filling_available',
        'retargeting_available',
        'ground_truth_location'
    ]
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)

    print(f"Created dataset split: {len(train_set)} Training, {len(test_set)} Testing (Seed={RANDOM_SEED})")
    print(f"Saved split metadata to {out_csv}")
    return True

if __name__ == "__main__":
    split_dataset()
