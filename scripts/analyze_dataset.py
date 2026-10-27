import glob
import scipy.io
import os
from collections import defaultdict

def analyze():
    classes = ["MSA", "PD", "CTRL", "PSP"]
    for c in classes:
        files = glob.glob(f"data/raw/{c}/*.mat")
        subjects = defaultdict(list)
        for f in files:
            try:
                mat = scipy.io.loadmat(f)
                pid = str(mat["person_id"][0]) if "person_id" in mat else "unknown"
                tid = str(mat["trial_id"][0]) if "trial_id" in mat else "unknown"
                subjects[pid].append(tid)
            except Exception as e:
                print(f"Error reading {f}: {e}")
        
        print(f"\n--- Class: {c} ---")
        print(f"Total recordings: {len(files)}")
        print(f"Unique participants ({len(subjects)}): {sorted(list(subjects.keys()))}")
        trials_per_sub = [len(v) for v in subjects.values()]
        print(f"Recordings per participant: min={min(trials_per_sub)}, max={max(trials_per_sub)}, avg={sum(trials_per_sub)/len(trials_per_sub):.1f}")

if __name__ == "__main__":
    analyze()
