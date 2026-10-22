import os
import sys
import subprocess
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PIPELINE_STEPS = [
    ("Step 1: Verify CMU Candidate Motions", "verify_cmu_dataset.py"),
    ("Step 2: Download Verified CMU Data", "download_cmu.py"),
    ("Step 3: Standardize BVH & Create Clean Ground Truth", "standardize_bvh.py"),
    ("Step 4: Generate Synthetic Noisy Benchmarks", "generate_noise.py"),
    ("Step 5: Generate Gap-Filling Occlusion Benchmarks", "generate_gaps.py"),
    ("Step 6: Generate Retargeted Proportion Benchmarks", "generate_retargeted.py"),
    ("Step 7: Create Train/Test Dataset Split", "split_dataset.py"),
    ("Step 8: Execute End-to-End Integrity Validation", "validate_dataset.py"),
    ("Step 9: Compile Final Reports & Manifest", "generate_reports_and_manifest.py")
]

def run_pipeline():
    print("=" * 80)
    print("MOTIONFORGE — COMPLETE REPRODUCIBLE DATASET GENERATION PIPELINE")
    print("=" * 80)
    start_time = time.time()

    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    for idx, (title, script_name) in enumerate(PIPELINE_STEPS, 1):
        script_path = os.path.join(scripts_dir, script_name)
        print(f"\n[{idx}/{len(PIPELINE_STEPS)}] EXECUTING: {title} ({script_name})...")
        print("-" * 80)

        cmd = [sys.executable, script_path]
        ret = subprocess.run(cmd, cwd=os.path.dirname(scripts_dir))

        if ret.returncode != 0:
            print(f"\n[PIPELINE ERROR] Pipeline aborted at Step {idx}: {title} failed with return code {ret.returncode}.")
            sys.exit(ret.returncode)

        print(f"[{idx}/{len(PIPELINE_STEPS)}] COMPLETED: {title}")

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"PIPELINE SUCCESS: MOTIONFORGE dataset generated and validated in {elapsed}s.")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()
