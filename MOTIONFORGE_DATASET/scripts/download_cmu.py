import os
import sys
import time
import requests
import urllib3

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MOTIONS = [
    (1, 7, 1, "walk"),
    (2, 7, 4, "slow walk"),
    (3, 8, 7, "walk, exaggerated stride"),
    (4, 8, 9, "walk"),
    (5, 9, 1, "run"),
    (6, 9, 5, "run"),
    (7, 16, 1, "jump"),
    (8, 16, 3, "high jump"),
    (9, 16, 5, "forward jump"),
    (10, 16, 8, "run/jog, sudden stop"),
    (11, 16, 11, "walk, veer left"),
    (12, 35, 14, "walk"),
    (13, 35, 33, "walk"),
    (14, 35, 27, "navigate around obstacles"),
    (15, 38, 3, "run around in a circle"),
    (16, 38, 4, "walk around, frequent turns, cyclic walk along a line"),
    (17, 49, 2, "jump up and down, hop on one foot"),
    (18, 49, 4, "run, leap"),
    (19, 49, 6, "cartwheel"),
    (20, 60, 1, "salsa dance"),
    (21, 60, 2, "salsa dance"),
    (22, 75, 1, "run jump"),
    (23, 75, 6, "180 jump"),
    (24, 86, 3, "walking, running, jumping, kicking, and stretching"),
    (25, 86, 6, "walking, running, kicking, punching, knee kicking, and stretching"),
    (26, 103, 3, "charleston_01"),
    (27, 104, 1, "JogThrough"),
    (28, 127, 4, "Walk to Run"),
    (29, 140, 8, "Get Up From Ground Laying on Back"),
    (30, 144, 20, "Punch_Sequence")
]

BASE_CMU_URL = "https://mocap.cs.cmu.edu"
BASE_BVH_URL = "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data"

def download_file(url, out_path, is_cmu=False):
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return True
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        resp = requests.get(url, verify=not is_cmu, timeout=30)
        if resp.status_code == 200:
            with open(out_path, 'wb') as f:
                f.write(resp.content)
            return True
        else:
            print(f"Failed to download {url}: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def run_download():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 3: DOWNLOAD ORIGINAL & VERIFIED MOTION DATA")
    print("=" * 70)
    
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    source_dir = os.path.join(workspace_root, "source", "cmu_original")
    os.makedirs(source_dir, exist_ok=True)
    
    success_count = 0
    total = len(MOTIONS)
    
    for idx, s, t, desc in MOTIONS:
        motion_id = f"MF{idx:03d}"
        dir_name = f"subject_{s:02d}_trial_{t:02d}"
        target_dir = os.path.join(source_dir, dir_name)
        os.makedirs(target_dir, exist_ok=True)
        
        print(f"[{idx}/{total}] Processing {motion_id} (Subject {s}, Trial {t}: '{desc}')...")
        
        # 1. Download official CMU ASF
        asf_url = f"{BASE_CMU_URL}/subjects/{s:02d}/{s:02d}.asf"
        asf_path = os.path.join(target_dir, f"{s:02d}.asf")
        asf_ok = download_file(asf_url, asf_path, is_cmu=True)
        
        # 2. Download official CMU AMC
        amc_url = f"{BASE_CMU_URL}/subjects/{s:02d}/{s:02d}_{t:02d}.amc"
        amc_path = os.path.join(target_dir, f"{s:02d}_{t:02d}.amc")
        amc_ok = download_file(amc_url, amc_path, is_cmu=True)
        
        # 3. Download verified standard BVH representation
        bvh_url = f"{BASE_BVH_URL}/{s:03d}/{s:02d}_{t:02d}.bvh"
        bvh_path = os.path.join(target_dir, f"{s:02d}_{t:02d}.bvh")
        bvh_ok = download_file(bvh_url, bvh_path, is_cmu=False)
        
        if bvh_ok:
            success_count += 1
            print(f"  [OK] Downloaded successfully: ASF={asf_ok}, AMC={amc_ok}, BVH={bvh_ok} -> {target_dir}")
        else:
            print(f"  [FAIL] Failed to download verified BVH for {motion_id}")
            
    print("-" * 70)
    print(f"STAGE 3 COMPLETE: Successfully downloaded {success_count}/{total} motion sequences.")
    print("-" * 70)
    return success_count == total

if __name__ == "__main__":
    success = run_download()
    if not success:
        sys.exit(1)
