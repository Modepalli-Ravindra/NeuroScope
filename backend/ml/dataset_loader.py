import os
import glob
import scipy.io
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from backend.ml.feature_extractor import extract_all_features, GYRO_CHANNELS

def load_single_mat(filepath: str) -> Dict[str, Any]:
    """Load and validate a single finger-tapping MAT file."""
    mat = scipy.io.loadmat(filepath)
    
    # Extract metadata safely
    diagnosis = str(mat["diagnosis"][0]).strip() if "diagnosis" in mat else "UNKNOWN"
    person_id = str(mat["person_id"][0]).strip() if "person_id" in mat else os.path.basename(filepath).split("_")[0]
    trial_id = str(mat["trial_id"][0]).strip() if "trial_id" in mat else "trial1"
    
    fs = 200.0
    if "fs" in mat:
        fs_val = mat["fs"]
        if isinstance(fs_val, np.ndarray):
            fs = float(fs_val.flatten()[0])
        else:
            fs = float(fs_val)

    # Extract 6 gyroscope channels
    signals: Dict[str, np.ndarray] = {}
    signal_lengths = []
    for ch in GYRO_CHANNELS:
        if ch in mat:
            arr = np.asarray(mat[ch], dtype=np.float64).flatten()
            signals[ch] = arr
            signal_lengths.append(len(arr))
        else:
            raise ValueError(f"Missing required channel {ch} in {filepath}")

    # Check minimum recording length (e.g., at least 2 seconds = 400 samples)
    min_len = min(signal_lengths)
    if min_len < int(fs * 2.0):
        raise ValueError(f"Recording {filepath} is too short ({min_len} samples at {fs} Hz)")

    # Align signal lengths if slight variance exists
    for ch in signals:
        signals[ch] = signals[ch][:min_len]

    return {
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "diagnosis": diagnosis,
        "person_id": person_id,
        "trial_id": trial_id,
        "fs": fs,
        "duration_sec": min_len / fs,
        "num_samples": min_len,
        "signals": signals
    }

def build_dataset_dataframe(data_dir: str, target_classes: List[str] = ["MSA", "PD"]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Parse all MAT files for the target classes, extract features, and return
    a clean pandas DataFrame containing features, diagnosis, person_id, and metadata.
    """
    records = []
    stats = {
        "classes": target_classes,
        "total_recordings": 0,
        "class_counts": {},
        "unique_participants": {},
        "invalid_recordings": 0
    }

    for cls in target_classes:
        cls_dir = os.path.join(data_dir, cls)
        if not os.path.isdir(cls_dir):
            continue
            
        mat_files = sorted(glob.glob(os.path.join(cls_dir, "*.mat")))
        participants = set()
        valid_cls_count = 0

        for fpath in mat_files:
            try:
                item = load_single_mat(fpath)
                feats = extract_all_features(item["signals"], item["fs"])
                
                # Combine metadata and features into a row dict
                row = {
                    "filename": item["filename"],
                    "diagnosis": item["diagnosis"],
                    "person_id": item["person_id"],
                    "trial_id": item["trial_id"],
                    "duration_sec": item["duration_sec"],
                    "fs": item["fs"]
                }
                row.update(feats)
                records.append(row)
                
                participants.add(item["person_id"])
                valid_cls_count += 1
            except Exception as e:
                stats["invalid_recordings"] += 1
                print(f"Skipping {fpath} due to error: {e}")

        stats["class_counts"][cls] = valid_cls_count
        stats["unique_participants"][cls] = len(participants)
        stats["total_recordings"] += valid_cls_count

    df = pd.DataFrame(records)
    return df, stats

if __name__ == "__main__":
    raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "raw")
    df, stats = build_dataset_dataframe(raw_dir, ["MSA", "PD"])
    print(f"Built dataset with {len(df)} rows and {len(df.columns)} columns.")
    print("Class statistics:", stats)
    print("Features extracted:", [c for c in df.columns if c not in ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"]][:10])
