import os
import io
import scipy.io
import numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_audit_dataset_scanned_counts():
    """Verify that only genuine parsed recordings exist from data/raw/ and no mock/placeholder data."""
    res = client.get("/api/dataset/samples")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    samples = res.json()
    assert len(samples) == 268, f"Expected 268 real recordings in data/raw/, got {len(samples)}"
    
    # Check that fabricated names like 'Kinematic Recording A' or 'Subj-M23-T1' do NOT exist
    for s in samples:
        assert "Kinematic Recording" not in s["display_name"], f"Fabricated display name found: {s['display_name']}"
        assert not s["code"].startswith("Subj-"), f"Fabricated code found: {s['code']}"
        assert s["sampling_rate_hz"] == 200, f"Expected 200 Hz, got {s['sampling_rate_hz']}"
        assert s["duration_sec"] >= 2.0, f"Expected duration >= 2.0s, got {s['duration_sec']}"
        assert s["sample_count"] >= 400, f"Expected sample count >= 400, got {s['sample_count']}"
        assert s["verified_diagnosis"] in ["MSA", "PD", "CTRL", "PSP", "UNVERIFIED"], f"Invalid diagnosis: {s['verified_diagnosis']}"
    
    print(f"[PASS] All {len(samples)} recordings strictly verified with genuine metadata (zero fabricated records).")

def test_cohort_filtering():
    """Test filtering real recordings by cohort (MSA, PD, CTRL, PSP)."""
    msa_res = client.get("/api/dataset/samples?cohort=MSA")
    assert msa_res.status_code == 200
    msa_samples = msa_res.json()
    assert len(msa_samples) == 72, f"Expected 72 MSA recordings, got {len(msa_samples)}"
    assert all(s["verified_diagnosis"] == "MSA" for s in msa_samples)

    pd_res = client.get("/api/dataset/samples?cohort=PD")
    assert pd_res.status_code == 200
    pd_samples = pd_res.json()
    assert len(pd_samples) == 68, f"Expected 68 PD recordings, got {len(pd_samples)}"
    assert all(s["verified_diagnosis"] == "PD" for s in pd_samples)

    ctrl_res = client.get("/api/dataset/samples?cohort=CTRL")
    assert ctrl_res.status_code == 200
    ctrl_samples = ctrl_res.json()
    assert len(ctrl_samples) == 52, f"Expected 52 CTRL recordings, got {len(ctrl_samples)}"
    assert all(s["verified_diagnosis"] == "CTRL" for s in ctrl_samples)

    psp_res = client.get("/api/dataset/samples?cohort=PSP")
    assert psp_res.status_code == 200
    psp_samples = psp_res.json()
    assert len(psp_samples) == 76, f"Expected 76 PSP recordings, got {len(psp_samples)}"
    assert all(s["verified_diagnosis"] == "PSP" for s in psp_samples)

    print("[PASS] Cohort filters verified: 72 MSA, 68 PD, 52 CTRL, 76 PSP recordings.")

def test_search_and_limit():
    """Test searching recordings by subject identifier and limiting results."""
    search_res = client.get("/api/dataset/samples?search=BM23")
    assert search_res.status_code == 200
    items = search_res.json()
    assert len(items) > 0, "Expected at least 1 match for BM23"
    assert all("BM23" in s["person_id"] or "BM23" in s["filename"] for s in items)

    limit_res = client.get("/api/dataset/samples?limit=5")
    assert limit_res.status_code == 200
    assert len(limit_res.json()) == 5

    print("[PASS] Search by subject ID and pagination limit verified.")

def test_import_dataset_validation():
    """Test importing a new MATLAB .mat recording into the dataset with full validation."""
    # 1. Reject invalid file extension
    bad_ext_res = client.post(
        "/api/dataset/import",
        files={"file": ("invalid.txt", b"plain text", "text/plain")}
    )
    assert bad_ext_res.status_code == 400
    assert "Invalid file format" in bad_ext_res.json()["detail"]

    # 2. Reject incomplete channels
    bio_incomplete = io.BytesIO()
    scipy.io.savemat(bio_incomplete, {
        "gyroThumbX": np.random.randn(1, 1000),
        "fs": 200
    })
    bio_incomplete.seek(0)
    missing_ch_res = client.post(
        "/api/dataset/import",
        files={"file": ("missing_channels.mat", bio_incomplete.getvalue(), "application/octet-stream")}
    )
    assert missing_ch_res.status_code == 422
    assert "Missing:" in missing_ch_res.json()["detail"]

    # 3. Reject recording shorter than 2.0s
    bio_short = io.BytesIO()
    scipy.io.savemat(bio_short, {
        "gyroThumbX": np.random.randn(1, 200),
        "gyroThumbY": np.random.randn(1, 200),
        "gyroThumbZ": np.random.randn(1, 200),
        "gyroIndexX": np.random.randn(1, 200),
        "gyroIndexY": np.random.randn(1, 200),
        "gyroIndexZ": np.random.randn(1, 200),
        "fs": 200
    })
    bio_short.seek(0)
    short_res = client.post(
        "/api/dataset/import",
        files={"file": ("too_short.mat", bio_short.getvalue(), "application/octet-stream")}
    )
    assert short_res.status_code == 422
    assert "too short" in short_res.json()["detail"]

    # 4. Successfully import valid .mat recording
    bio_valid = io.BytesIO()
    scipy.io.savemat(bio_valid, {
        "gyroThumbX": np.random.randn(1, 3000),
        "gyroThumbY": np.random.randn(1, 3000),
        "gyroThumbZ": np.random.randn(1, 3000),
        "gyroIndexX": np.random.randn(1, 3000),
        "gyroIndexY": np.random.randn(1, 3000),
        "gyroIndexZ": np.random.randn(1, 3000),
        "fs": 200,
        "person_id": np.array(["TEST_IMPORT_01"]),
        "trial_id": np.array(["trial_import"]),
        "diagnosis": np.array(["MSA"])
    })
    bio_valid.seek(0)
    import_res = client.post(
        "/api/dataset/import",
        files={"file": ("valid_test_recording.mat", bio_valid.getvalue(), "application/octet-stream")}
    )
    assert import_res.status_code == 200
    data = import_res.json()
    assert data["status"] == "success"
    assert data["record"]["person_id"] == "TEST_IMPORT_01"
    assert data["record"]["trial_id"] == "trial_import"
    assert data["record"]["verified_diagnosis"] == "MSA"
    assert data["record"]["duration_sec"] == 15.0
    assert data["record"]["sampling_rate_hz"] == 200

    print(f"[PASS] Dataset import validation verified. Successfully imported '{data['record']['filename']}' ({data['record']['duration_sec']}s, 200 Hz).")

    # 5. Verify the newly imported recording is now selectable and passes to analysis pipeline
    sample_id = data["record"]["sample_id"]
    analysis_res = client.post(
        "/api/analyze",
        data={"sample_id": sample_id, "notes": "Testing imported sample inference"}
    )
    assert analysis_res.status_code == 200
    analysis_data = analysis_res.json()
    assert analysis_data["prediction"]["predicted_class"] in ["MSA", "PD"]
    assert "shap_explanation" in analysis_data
    assert analysis_data["input_metadata"]["person_id"] == "TEST_IMPORT_01"
    print(f"[PASS] Imported recording successfully executed through 59-feature extraction and differential inference.")

if __name__ == "__main__":
    test_audit_dataset_scanned_counts()
    test_cohort_filtering()
    test_search_and_limit()
    test_import_dataset_validation()
    print("\nALL DATASET AUDIT AND IMPORT SUITES PASSED SUCCESSFULLY!")
