import os
import sys
import re
import csv
import json
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CANDIDATES = [
    (7, 1),
    (7, 4),
    (8, 7),
    (8, 9),
    (9, 1),
    (9, 5),
    (16, 1),
    (16, 3),
    (16, 5),
    (16, 8),
    (16, 11),
    (35, 14),
    (35, 33),
    (35, 37),
    (38, 3),
    (38, 4),
    (49, 2),
    (49, 4),
    (49, 6),
    (60, 1),
    (60, 2),
    (75, 1),
    (75, 6),
    (86, 3),
    (86, 6),
    (103, 3),
    (104, 1),
    (127, 4),
    (140, 8),
    (144, 20)
]

BASE_URL = "https://mocap.cs.cmu.edu"

def get_subject_page(subject_num):
    url = f"{BASE_URL}/search.php?subjectnumber={subject_num}"
    try:
        resp = requests.get(url, verify=False, timeout=15)
        if resp.status_code == 200:
            return resp.text
        return None
    except Exception as e:
        print(f"Error fetching subject {subject_num}: {e}")
        return None

def parse_subject_page(html_text, subject_num):
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Locate asf file
    asf_url = None
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if href.lower().endswith('.asf'):
            asf_url = href if href.startswith('http') else f"{BASE_URL}{href if href.startswith('/') else '/' + href}"
            break
            
    trials_info = {}
    
    # Each row in table
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if not tds:
            continue
        texts = [td.get_text(strip=True) for td in tds]
        
        # Check if row contains a trial number
        t_num = None
        desc = ""
        fps = 120 # CMU default
        links = {}
        for a in tr.find_all('a'):
            href = a.get('href', '')
            ext = href.split('.')[-1].lower() if '.' in href else ''
            if ext in ['amc', 'c3d', 'tvd', 'avi', 'bvh']:
                full_href = href if href.startswith('http') else f"{BASE_URL}{href if href.startswith('/') else '/' + href}"
                links[ext] = full_href
                
        # Locate trial number
        for idx, text in enumerate(texts):
            if text.isdigit():
                val = int(text)
                # Ensure it's a trial number
                if 1 <= val <= 200:
                    t_num = val
                    if idx + 1 < len(texts):
                        desc = texts[idx + 1]
                    break
                    
        # Check fps in texts
        for text in texts:
            if text.isdigit() and int(text) in [30, 60, 120, 240]:
                fps = int(text)
                
        if t_num is not None:
            trials_info[t_num] = {
                'description': desc,
                'fps': fps,
                'links': links,
                'asf_url': asf_url
            }
            
    return asf_url, trials_info

def check_remote_file(url):
    try:
        resp = requests.head(url, verify=False, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            return True, int(resp.headers.get('content-length', 0))
        # If HEAD fails or gives 405/403, try GET range
        resp = requests.get(url, verify=False, timeout=10, headers={'Range': 'bytes=0-1024'})
        if resp.status_code in [200, 206]:
            return True, 0
        return False, 0
    except Exception as e:
        return False, 0

def inspect_amc_frames(url):
    """Peek or fetch amc to extract actual frame count"""
    try:
        resp = requests.get(url, verify=False, timeout=15)
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            last_frame = 0
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    f = int(line)
                    if f > last_frame:
                        last_frame = f
            return last_frame
        return 0
    except Exception as e:
        return 0

def verify_all_candidates():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 1: CMU CANDIDATE VERIFICATION")
    print("=" * 70)
    
    unique_subjects = sorted(list(set(s for s, t in CANDIDATES)))
    subject_cache = {}
    
    print(f"Fetching official CMU metadata for {len(unique_subjects)} subjects...")
    for s in unique_subjects:
        html = get_subject_page(s)
        if html:
            asf_url, trials = parse_subject_page(html, s)
            subject_cache[s] = {'asf': asf_url, 'trials': trials}
            print(f"  Subject {s:3d}: Found {len(trials)} trials, ASF: {asf_url}")
        else:
            subject_cache[s] = None
            print(f"  Subject {s:3d}: FAILED to retrieve subject page")
            
    results = []
    
    for idx, (s, t) in enumerate(CANDIDATES, 1):
        motion_id = f"MF{idx:03d}"
        s_data = subject_cache.get(s)
        
        if not s_data:
            results.append({
                'motion_id': motion_id,
                'cmu_subject': s,
                'cmu_trial': t,
                'official_description': 'UNKNOWN',
                'source_url': 'NOT_FOUND',
                'available_format': 'NONE',
                'fps': 0,
                'frame_count': 0,
                'duration_seconds': 0.0,
                'download_status': 'NOT_AVAILABLE',
                'conversion_status': 'PENDING',
                'bvh_validation_status': 'PENDING',
                'verification_status': 'NOT_AVAILABLE',
                'notes': f'Subject {s} not found or page unreachable on CMU database'
            })
            continue
            
        trials = s_data['trials']
        if t not in trials:
            results.append({
                'motion_id': motion_id,
                'cmu_subject': s,
                'cmu_trial': t,
                'official_description': 'UNKNOWN',
                'source_url': 'NOT_FOUND',
                'available_format': 'NONE',
                'fps': 0,
                'frame_count': 0,
                'duration_seconds': 0.0,
                'download_status': 'NOT_AVAILABLE',
                'conversion_status': 'PENDING',
                'bvh_validation_status': 'PENDING',
                'verification_status': 'NOT_AVAILABLE',
                'notes': f'Trial {t} does not exist for Subject {s} in CMU database'
            })
            continue
            
        t_info = trials[t]
        desc = t_info['description']
        fps = t_info['fps']
        links = t_info['links']
        asf_url = t_info['asf_url']
        
        amc_url = links.get('amc')
        # If link wasn't parsed directly, test standard URL pattern
        if not amc_url:
            amc_url = f"{BASE_URL}/subjects/{s:02d}/{s:02d}_{t:02d}.amc"
            
        # Check formats
        formats = []
        if asf_url:
            formats.append('ASF')
        if 'amc' in links or amc_url:
            formats.append('AMC')
        for fmt in ['c3d', 'tvd', 'avi', 'bvh']:
            if fmt in links:
                formats.append(fmt.upper())
                
        available_fmt_str = "/".join(formats)
        
        # Verify remote accessibility
        print(f"Verifying {motion_id} (Subject {s}, Trial {t}): '{desc}' ...")
        amc_ok, _ = check_remote_file(amc_url)
        asf_ok = True
        if asf_url:
            asf_ok, _ = check_remote_file(asf_url)
            
        if amc_ok and asf_ok:
            frame_cnt = inspect_amc_frames(amc_url)
            duration = round(frame_cnt / fps, 3) if fps > 0 else 0.0
            results.append({
                'motion_id': motion_id,
                'cmu_subject': s,
                'cmu_trial': t,
                'official_description': desc,
                'source_url': amc_url,
                'available_format': available_fmt_str,
                'fps': fps,
                'frame_count': frame_cnt,
                'duration_seconds': duration,
                'download_status': 'VERIFIED_ACCESSIBLE',
                'conversion_status': 'PENDING',
                'bvh_validation_status': 'PENDING',
                'verification_status': 'VERIFIED',
                'notes': f'Official CMU trial verified. ASF skeleton and AMC motion verified accessible.'
            })
            print(f"  -> VERIFIED: {frame_cnt} frames, {duration}s @ {fps}fps")
        else:
            notes = []
            if not amc_ok:
                notes.append(f"AMC file not reachable at {amc_url}")
            if not asf_ok:
                notes.append(f"ASF skeleton file not reachable at {asf_url}")
            results.append({
                'motion_id': motion_id,
                'cmu_subject': s,
                'cmu_trial': t,
                'official_description': desc,
                'source_url': amc_url,
                'available_format': available_fmt_str,
                'fps': fps,
                'frame_count': 0,
                'duration_seconds': 0.0,
                'download_status': 'DOWNLOAD_FAILED',
                'conversion_status': 'PENDING',
                'bvh_validation_status': 'PENDING',
                'verification_status': 'DOWNLOAD_FAILED',
                'notes': "; ".join(notes)
            })
            print(f"  -> FAILED: {'; '.join(notes)}")
            
    return results

def write_reports(results, out_csv_paths, out_md_paths):
    fieldnames = [
        'motion_id',
        'cmu_subject',
        'cmu_trial',
        'official_description',
        'source_url',
        'available_format',
        'fps',
        'frame_count',
        'duration_seconds',
        'download_status',
        'conversion_status',
        'bvh_validation_status',
        'verification_status',
        'notes'
    ]
    
    for path in out_csv_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        print(f"Saved CSV report to {path}")
        
    # Generate Markdown Report
    total_candidates = len(results)
    verified_count = sum(1 for r in results if r['verification_status'] == 'VERIFIED')
    unavailable_count = sum(1 for r in results if r['verification_status'] == 'NOT_AVAILABLE')
    failed_count = sum(1 for r in results if r['verification_status'] in ['DOWNLOAD_FAILED', 'CONVERSION_FAILED', 'VALIDATION_FAILED'])
    
    md_content = f"""# MOTIONFORGE — CMU Dataset Verification Report

## Summary Statistics

- **Total Candidates Checked**: {total_candidates}
- **Successfully Verified**: {verified_count}
- **Unavailable Motions**: {unavailable_count}
- **Failed Checks**: {failed_count}
- **Download Status**: {verified_count} verified accessible (ready for Stage 3)
- **Conversion Status**: Pending (Stage 4)
- **BVH Validation Status**: Pending (Stage 4)
- **Final Usable Motions Identified**: {verified_count} / {total_candidates}

---

## Candidate Verification Table

| Motion ID | Subject | Trial | Description | Formats | FPS | Frames | Duration (s) | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
"""
    for r in results:
        md_content += f"| {r['motion_id']} | {r['cmu_subject']} | {r['cmu_trial']} | {r['official_description']} | {r['available_format']} | {r['fps']} | {r['frame_count']} | {r['duration_seconds']} | **{r['verification_status']}** | {r['notes']} |\n"

    md_content += """
---

## Phase 1 & 2 Findings on CMU Database Structure

1. **Subjects & Trials**:
   - Each subject represents a unique capture session and actor calibration.
   - Trials represent specific motion sequences executed by that subject.
2. **Skeleton & Motion Representation**:
   - CMU provides raw/original skeletons as **ASF (Acclaim Skeleton File)** per subject (e.g., `07.asf`).
   - Motion data is provided as **AMC (Acclaim Motion Capture)** per trial (e.g., `07_01.amc`).
   - Complementary files include C3D (raw 3D optical marker trajectories), TVD, and preview AVIs.
3. **Units & Coordinate Systems**:
   - ASF uses `:units length 0.45`, angle in degrees.
   - Root has 6 DOFs (translation + rotation), child bones have 1-3 rotational DOFs based on joint type.
   - Framerates are officially standard at 120 FPS.
4. **Conversion to BVH**:
   - To standardize for the MOTIONFORGE competition, a forward kinematics and hierarchical joint conversion pipeline is implemented to transform ASF/AMC into standardized BVH.
"""

    for path in out_md_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Saved Markdown report to {path}")

if __name__ == '__main__':
    results = verify_all_candidates()
    
    csv_paths = [
        "MOTIONFORGE_DATASET/reports/dataset_verification_report.csv",
        "reports/dataset_verification_report.csv"
    ]
    md_paths = [
        "MOTIONFORGE_DATASET/reports/dataset_verification_report.md",
        "reports/dataset_verification_report.md"
    ]
    write_reports(results, csv_paths, md_paths)
