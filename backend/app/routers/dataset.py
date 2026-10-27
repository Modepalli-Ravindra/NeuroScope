import os
import glob
import io
import time
import shutil
import scipy.io
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/dataset", tags=["Dataset"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
REQUIRED_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]

# Global cache for scanned real dataset files
_DATASET_CACHE: Dict[str, Dict[str, Any]] = {}
_LAST_SCAN_TIME: float = 0.0

# Legacy alias mapping to maintain 100% compatibility with existing test suites
LEGACY_ALIASES = {
    "msa_sample_1": "MSA/MSABM23_1.mat",
    "msa_sample_2": "MSA/MSAJM16_1.mat",
    "msa_sample_3": "MSA/MSANJ09_2.mat",
    "pd_sample_1": "PD/PDBS13_1.mat",
    "pd_sample_2": "PD/PDJP10_1.mat",
    "pd_sample_3": "PD/PDRM21_2.mat",
    "ctrl_sample_1": "CTRL/CTRLAM21_1.mat",
    "psp_sample_1": "PSP/PSPBM22_1.mat"
}

def scan_real_dataset(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Dynamically scan the data/raw directory and parse verified recordings from actual .mat files.
    Extracts real subject identifiers, trial IDs, verified diagnosis labels, and durations.
    Never invents or fabricates records.
    """
    global _DATASET_CACHE, _LAST_SCAN_TIME
    
    # Return cache if scanned within last 30 seconds unless force_refresh is requested
    current_time = time.time()
    if not force_refresh and _DATASET_CACHE and (current_time - _LAST_SCAN_TIME < 30.0):
        return _DATASET_CACHE

    scanned_records: Dict[str, Dict[str, Any]] = {}
    
    if not os.path.exists(DATA_DIR):
        _DATASET_CACHE = {}
        _LAST_SCAN_TIME = current_time
        return scanned_records

    for root, _, files in os.walk(DATA_DIR):
        for f in sorted(files):
            if f.lower().endswith(".mat"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, DATA_DIR).replace("\\", "/")
                
                try:
                    mat = scipy.io.loadmat(full_path)
                    
                    # 1. Validate all 6 gyroscope channels exist
                    if not all(ch in mat for ch in REQUIRED_CHANNELS):
                        continue
                        
                    # 2. Extract genuine sampling frequency fs
                    fs = 200.0
                    if "fs" in mat:
                        fs_val = mat["fs"]
                        if isinstance(fs_val, np.ndarray):
                            fs = float(fs_val.flatten()[0])
                        else:
                            fs = float(fs_val)
                    if fs <= 0:
                        fs = 200.0

                    # 3. Check channel sample lengths and minimum required duration (2.0s)
                    lengths = [np.asarray(mat[ch]).size for ch in REQUIRED_CHANNELS]
                    min_len = min(lengths)
                    if min_len < int(fs * 2.0):
                        continue
                        
                    duration_sec = round(float(min_len) / float(fs), 2)
                    sample_count = int(min_len)

                    # 4. Extract genuine person_id from metadata or filename
                    person_id = ""
                    if "person_id" in mat:
                        p_val = mat["person_id"]
                        if isinstance(p_val, np.ndarray) and p_val.size > 0:
                            person_id = str(p_val.flatten()[0]).strip()
                    if not person_id:
                        person_id = os.path.splitext(f)[0].split("_")[0]

                    # 5. Extract genuine trial_id
                    trial_id = "trial1"
                    if "trial_id" in mat:
                        t_val = mat["trial_id"]
                        if isinstance(t_val, np.ndarray) and t_val.size > 0:
                            trial_id = str(t_val.flatten()[0]).strip()
                    else:
                        parts = os.path.splitext(f)[0].split("_")
                        if len(parts) > 1:
                            trial_id = f"trial{parts[1]}"

                    # 6. Extract verified diagnosis label (never invent labels)
                    verified_diagnosis = "UNVERIFIED"
                    if "diagnosis" in mat:
                        d_val = mat["diagnosis"]
                        if isinstance(d_val, np.ndarray) and d_val.size > 0:
                            d_str = str(d_val.flatten()[0]).strip().upper()
                            if d_str in ["MSA", "PD", "CTRL", "PSP"]:
                                verified_diagnosis = d_str
                    
                    if verified_diagnosis == "UNVERIFIED":
                        # Check directory structure for genuine Belgrade dataset partitions
                        parent_dir = os.path.basename(root).upper()
                        if parent_dir in ["MSA", "PD", "CTRL", "PSP"]:
                            verified_diagnosis = parent_dir

                    # Unique deterministic sample ID based on sanitized relative path
                    sample_id = rel_path.replace("/", "__").replace("\\", "__")
                    file_size_kb = round(os.path.getsize(full_path) / 1024.0, 1)

                    record = {
                        "sample_id": sample_id,
                        "filename": f,
                        "rel_path": rel_path,
                        "person_id": person_id,
                        "trial_id": trial_id,
                        "verified_diagnosis": verified_diagnosis,
                        "display_name": f"{person_id} ({trial_id})",
                        "code": os.path.splitext(f)[0],
                        "duration_sec": duration_sec,
                        "sample_count": sample_count,
                        "sampling_rate_hz": int(fs),
                        "sampling_rate": f"{int(fs)} Hz",
                        "file_size_kb": file_size_kb,
                        "description": (
                            f"Verified {verified_diagnosis} recording • {person_id} {trial_id} • "
                            f"{duration_sec}s at {int(fs)} Hz ({sample_count:,} samples)"
                            if verified_diagnosis != "UNVERIFIED"
                            else f"Imported recording • {person_id} • {duration_sec}s ({int(fs)} Hz)"
                        )
                    }
                    scanned_records[sample_id] = record
                    
                except Exception as e:
                    # Skip unparseable files without crashing
                    continue

    _DATASET_CACHE = scanned_records
    _LAST_SCAN_TIME = current_time
    return _DATASET_CACHE

def get_real_sample_by_id(sample_id: str) -> Optional[Dict[str, Any]]:
    """
    Look up a real parsed recording by sample_id, relative path, filename, or legacy alias.
    """
    cache = scan_real_dataset()
    
    # 1. Direct match in cache
    if sample_id in cache:
        return cache[sample_id]
        
    # 2. Check legacy alias
    if sample_id in LEGACY_ALIASES:
        target_rel = LEGACY_ALIASES[sample_id]
        for item in cache.values():
            if item["rel_path"] == target_rel:
                return item

    # 3. Match by rel_path or filename
    normalized_id = sample_id.replace("\\", "/")
    for item in cache.values():
        if item["rel_path"] == normalized_id or item["filename"] == sample_id:
            return item

    return None

@router.get("/info")
def get_dataset_info() -> Dict[str, Any]:
    """Return genuine dataset statistics, cohort distribution, and clinical limitations."""
    records = scan_real_dataset()
    
    cohort_counts = {"MSA": 0, "PD": 0, "CTRL": 0, "PSP": 0, "UNVERIFIED": 0}
    for r in records.values():
        diag = r.get("verified_diagnosis", "UNVERIFIED")
        if diag in cohort_counts:
            cohort_counts[diag] += 1
        else:
            cohort_counts[diag] = 1

    return {
        "dataset_name": "University of Belgrade Movement Disorders Kinematic Cohort",
        "citation": "Heliyon 9(4): e14824 (2023). DOI: 10.1016/j.heliyon.2023.e14824",
        "sensor_type": "6-Axis Gyroscope (Thumb + Index finger)",
        "sampling_rate_hz": 200,
        "total_verified_recordings": len(records),
        "classes_available": {k: v for k, v in cohort_counts.items() if v > 0},
        "primary_differential_classes": ["MSA", "PD"],
        "clinical_notes": {
            "msa_subtype_limitation": "The MSA cohort in this dataset is predominantly MSA-P (parkinsonian variant). Model results cannot be assumed to generalize to MSA-C (cerebellar variant).",
            "study_protocol": "Repetitive finger tapping task performed continuously for 15-30 seconds with miniature gyroscopes attached to thumb and index finger at 200 Hz.",
            "data_use": "Verified scientific dataset shared under research and academic evaluation terms."
        }
    }

@router.get("/samples")
def get_authentic_samples(
    cohort: Optional[str] = Query(None, description="Filter by verified diagnosis: MSA, PD, CTRL, PSP, UNVERIFIED, or all"),
    search: Optional[str] = Query(None, description="Search by subject ID, trial, or filename"),
    limit: Optional[int] = Query(None, description="Optional maximum number of samples to return")
) -> List[Dict[str, Any]]:
    """
    Return dynamically scanned real recordings from actual .mat files on disk.
    Contains verified metadata extracted directly from each recording.
    """
    records = scan_real_dataset()
    items = list(records.values())

    # Optional cohort filter
    if cohort and cohort.lower() != "all":
        target = cohort.upper()
        items = [i for i in items if i["verified_diagnosis"] == target]

    # Optional search query filter
    if search:
        s = search.lower().strip()
        items = [
            i for i in items
            if s in i["person_id"].lower()
            or s in i["filename"].lower()
            or s in i["code"].lower()
            or s in i["trial_id"].lower()
        ]

    # Optional limit
    if limit and limit > 0:
        items = items[:limit]

    return items

@router.post("/import")
async def import_dataset_recording(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Explicitly import and validate a .mat recording into the platform's dataset repository.
    Strictly verifies required 6 gyroscope channels (Thumb X,Y,Z and Index X,Y,Z) and sampling frequency.
    Extracts genuine metadata from the recording.
    """
    if not file.filename.lower().endswith(".mat"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only MATLAB .mat recordings containing 6-axis gyroscope channels are supported."
        )

    content = await file.read()
    if len(content) < 500:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or corrupted (size < 500 bytes).")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds maximum allowed upload size limit of 25 MB.")

    # 1. Parse in-memory with scipy.io to validate channels and metadata
    try:
        mat = scipy.io.loadmat(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Corrupted or invalid MATLAB .mat structure: {str(e)}")

    # 2. Verify all 6 required gyroscope channels
    missing_channels = [ch for ch in REQUIRED_CHANNELS if ch not in mat]
    if missing_channels:
        raise HTTPException(
            status_code=422,
            detail=f"Incomplete sensor channels. Missing: {', '.join(missing_channels)}. All 6 gyroscope channels (Thumb X,Y,Z & Index X,Y,Z) are mandatory."
        )

    # 3. Extract sampling rate fs
    fs = 200.0
    if "fs" in mat:
        fs_val = mat["fs"]
        if isinstance(fs_val, np.ndarray):
            fs = float(fs_val.flatten()[0])
        else:
            fs = float(fs_val)
    if fs <= 0:
        fs = 200.0

    # 4. Check duration
    lengths = [np.asarray(mat[ch]).size for ch in REQUIRED_CHANNELS]
    min_len = min(lengths)
    if min_len < int(fs * 2.0):
        raise HTTPException(
            status_code=422,
            detail=f"Recording duration too short: {min_len} samples ({min_len/fs:.1f}s). Minimum required is 2.0 seconds at {int(fs)} Hz."
        )

    duration_sec = round(float(min_len) / float(fs), 2)
    sample_count = int(min_len)

    # 5. Extract genuine person_id, trial_id, and diagnosis
    clean_filename = os.path.basename(file.filename)
    person_id = ""
    if "person_id" in mat:
        p_val = mat["person_id"]
        if isinstance(p_val, np.ndarray) and p_val.size > 0:
            person_id = str(p_val.flatten()[0]).strip()
    if not person_id:
        person_id = os.path.splitext(clean_filename)[0].split("_")[0]

    trial_id = "trial1"
    if "trial_id" in mat:
        t_val = mat["trial_id"]
        if isinstance(t_val, np.ndarray) and t_val.size > 0:
            trial_id = str(t_val.flatten()[0]).strip()

    verified_diagnosis = "UNVERIFIED"
    if "diagnosis" in mat:
        d_val = mat["diagnosis"]
        if isinstance(d_val, np.ndarray) and d_val.size > 0:
            d_str = str(d_val.flatten()[0]).strip().upper()
            if d_str in ["MSA", "PD", "CTRL", "PSP"]:
                verified_diagnosis = d_str

    # 6. Save verified recording to data/raw/imported/
    import_dir = os.path.join(DATA_DIR, "imported")
    os.makedirs(import_dir, exist_ok=True)
    dest_path = os.path.join(import_dir, clean_filename)

    # Avoid silent collisions by appending counter if needed
    base_name, ext = os.path.splitext(clean_filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(import_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    final_filename = os.path.basename(dest_path)
    with open(dest_path, "wb") as f_out:
        f_out.write(content)

    # 7. Force refresh cache
    updated_cache = scan_real_dataset(force_refresh=True)
    rel_path = os.path.relpath(dest_path, DATA_DIR).replace("\\", "/")
    sample_id = rel_path.replace("/", "__").replace("\\", "__")

    record = updated_cache.get(sample_id, {
        "sample_id": sample_id,
        "filename": final_filename,
        "rel_path": rel_path,
        "person_id": person_id,
        "trial_id": trial_id,
        "verified_diagnosis": verified_diagnosis,
        "duration_sec": duration_sec,
        "sample_count": sample_count,
        "sampling_rate_hz": int(fs),
        "sampling_rate": f"{int(fs)} Hz",
        "file_size_kb": round(len(content) / 1024.0, 1),
        "display_name": f"{person_id} ({trial_id})",
        "code": os.path.splitext(final_filename)[0],
        "description": f"Imported verified recording • {duration_sec}s at {int(fs)} Hz ({sample_count:,} samples)"
    })

    return {
        "status": "success",
        "message": f"Successfully imported '{final_filename}' with verified 6-axis gyroscope channels.",
        "record": record,
        "total_dataset_count": len(updated_cache)
    }
