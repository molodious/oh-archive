#!/usr/bin/env python3
"""
OH Archive Updater
Usage: python3 update_archive.py --oh 116 --clips "/mnt/c/Office Hours/OH116/clips/"

Reads clip filenames, maps to spreadsheet problems, updates data.json, 
commits and pushes to GitHub Pages.
"""

import json, re, os, subprocess, sys, argparse
from pathlib import Path
from datetime import date

ARCHIVE_DIR = Path(__file__).parent
DATA_FILE = ARCHIVE_DIR / "data.json"
GITHUB_REMOTE = "origin"  # uses existing remote config in repo

# Maps clip module name → (spreadsheet module name, chapter prefix)
MODULE_MAP = {
    'HVAC': {
        'Thermo':           ('Thermodynamics', '7'),
        'Fluids':           ('Fluids', '8'),
        'Psychrometrics':   ('Psychrometrics', '9'),
        'HeatTransfer':     ('Heat Transfer', '10'),
        'HVAC':             ('HVAC', '11'),
        'Systems':          ('Systems and Components', '12'),
        'SupportingTopics': ('Supporting Topics', '13'),
        'PracticeExam1':    ('Practice Exam #1', '14'),
        'PracticeExam2':    ('Practice Exam #2', '15'),
    },
    'TFS': {
        'Thermo':           ('Thermodynamics', '7'),
        'HeatTransfer':     ('Heat Transfer', '8'),
        'Fluids':           ('Hydraulic & Fluid Applications', '9'),
        'Energy':           ('Energy & Power System Applications', '10'),
        'SupportingTopics': ('Supporting Topics', '11'),
        'PracticeExam1':    ('Practice Exam #1', '12'),
        'PracticeExam2':    ('Practice Exam #2', '13'),
    }
}

def clip_to_problem(filename):
    """
    Convert clip filename to (program, module_name, problem_id).
    Example: 'HVAC-Thermo-4.mp4' → ('HVAC', 'Thermodynamics', '7-4')
    Example: 'TFS-Fluids-46.mp4' → ('TFS', 'Hydraulic & Fluid Applications', '9-46')
    """
    stem = Path(filename).stem  # remove .mp4
    parts = stem.split('-')
    if len(parts) < 3:
        return None

    program = parts[0]
    num = parts[-1]
    mod_key = '-'.join(parts[1:-1])

    if program not in MODULE_MAP:
        print(f"  ⚠️  Unknown program in clip: {filename}")
        return None

    if mod_key not in MODULE_MAP[program]:
        print(f"  ⚠️  Unknown module '{mod_key}' in clip: {filename}")
        return None

    module_name, chapter = MODULE_MAP[program][mod_key]
    problem_id = f"{chapter}-{num}"
    return (program, module_name, problem_id)


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(data):
    data['lastUpdated'] = date.today().isoformat()
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_oh_to_problems(data, oh_num, clips_dir):
    """Add oh_num to all problems identified from clip filenames."""
    clips_path = Path(clips_dir)
    clip_files = list(clips_path.glob('*.mp4'))
    
    if not clip_files:
        print(f"  ⚠️  No MP4 clips found in {clips_dir}")
        return []

    print(f"  Found {len(clip_files)} clips in {clips_dir}")
    
    updated = []
    for clip in clip_files:
        result = clip_to_problem(clip.name)
        if not result:
            continue
        
        program, module_name, problem_id = result
        
        # Find in data
        found = False
        for entry in data[program]:
            if entry['module'] == module_name and entry['problem'] == problem_id:
                if oh_num not in entry['oh']:
                    entry['oh'].append(oh_num)
                    entry['oh'].sort()
                    print(f"  ✅ Added OH{oh_num} to {program} {module_name} {problem_id}")
                    updated.append(f"{program} {problem_id}")
                else:
                    print(f"  ➡️  {program} {module_name} {problem_id} already has OH{oh_num}")
                found = True
                break
        
        if not found:
            print(f"  ❌ Problem not found in data: {program} {module_name} {problem_id} (from {clip.name})")
    
    return updated


def git_push(oh_num, updated_problems):
    """Commit and push to GitHub Pages."""
    os.chdir(ARCHIVE_DIR)
    
    msg = f"Add OH{oh_num} — {len(updated_problems)} problem(s) updated"
    
    subprocess.run(['git', 'add', 'data.json'], check=True)
    
    result = subprocess.run(['git', 'diff', '--cached', '--quiet'])
    if result.returncode == 0:
        print("  Nothing to commit (no changes).")
        return

    subprocess.run(['git', 'commit', '-m', msg], check=True)
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)
    print(f"  ✅ Pushed to GitHub Pages")


def main():
    parser = argparse.ArgumentParser(description='Update OH Archive with new session data')
    parser.add_argument('--oh', type=int, required=True, help='Office Hours number (e.g. 116)')
    parser.add_argument('--clips', type=str, help='Path to clips directory (optional; auto-detects from OH number)')
    args = parser.parse_args()

    oh_num = args.oh
    clips_dir = args.clips or f"/mnt/c/Office Hours/OH{oh_num}"
    
    # Check if clips dir exists
    if not Path(clips_dir).exists():
        print(f"❌ Clips directory not found: {clips_dir}")
        print(f"   Provide the path with --clips or ensure OH{oh_num} folder exists at default location.")
        sys.exit(1)

    print(f"\n📋 Updating OH Archive for OH{oh_num}")
    print(f"   Clips directory: {clips_dir}")
    print()

    data = load_data()
    updated = add_oh_to_problems(data, oh_num, clips_dir)
    
    if updated:
        save_data(data)
        print(f"\n💾 Saved data.json ({len(updated)} updates)")
        git_push(oh_num, updated)
        print(f"\n🌐 Live at: https://molodious.github.io/oh-archive/")
    else:
        print("\nNo updates made.")


if __name__ == '__main__':
    main()
