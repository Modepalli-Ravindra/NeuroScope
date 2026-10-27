import os
import io
import scipy.io
import numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["models_loaded"]["random_forest"] is True
    print("[PASS] Health check passed.")

def test_dataset_info():
    res = client.get("/api/dataset/info")
    assert res.status_code == 200
    data = res.json()
    assert "classes_available" in data
    assert data["classes_available"]["MSA"] == 72
    assert data["classes_available"]["PD"] == 68
    print("[PASS] Dataset info check passed.")

def test_samples():
    res = client.get("/api/dataset/samples")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) > 0
    print(f"[PASS] Sample list check passed ({len(samples)} samples available).")

def test_model_evaluation():
    res = client.get("/api/model/evaluation")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert any("Random Forest" in k for k in data["results"])
    assert any("Logistic Regression" in k for k in data["results"])
    print("[PASS] Model evaluation check passed (both RF and LR benchmark present).")

def test_analysis_with_sample():
    res = client.post("/api/analyze", data={"sample_id": "msa_sample_1", "notes": "Automated test"})
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"]["predicted_class"] in ["MSA", "PD"]
    assert "shap_explanation" in data
    assert len(data["shap_explanation"]["top_features"]) > 0
    print(f"[PASS] Analysis check passed. Predicted: {data['prediction']['predicted_class']}")

    analysis_id = data["id"]
    if analysis_id:
        # Check history
        h_res = client.get("/api/history")
        assert h_res.status_code == 200
        assert any(item["id"] == analysis_id for item in h_res.json())
        print(f"[PASS] History verification passed for record {analysis_id}.")

        # Check PDF report generation
        pdf_res = client.get(f"/api/reports/{analysis_id}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 1000
        print(f"[PASS] PDF report generation passed ({len(pdf_res.content)} bytes).")

def test_invalid_upload_handling():
    # 1. Non-MAT file
    res = client.post("/api/analyze", files={"file": ("test.txt", b"plain text content", "text/plain")})
    assert res.status_code == 400
    print("[PASS] Non-MAT file upload correctly rejected with 400.")

    # 2. Corrupt MAT file (>500 bytes of non-mat bytes)
    corrupt_bytes = b"CORRUPT_HEADER" + b"\x00" * 1024
    res = client.post("/api/analyze", files={"file": ("corrupt.mat", corrupt_bytes, "application/octet-stream")})
    assert res.status_code in [400, 422]
    print(f"[PASS] Corrupt MAT file rejected with status {res.status_code}.")

    # 3. Missing sensor channels in MAT
    bio = io.BytesIO()
    scipy.io.savemat(bio, {"gyroThumbX": np.random.randn(500)}) # missing other 5 channels
    bio.seek(0)
    res = client.post("/api/analyze", files={"file": ("incomplete.mat", bio.getvalue(), "application/octet-stream")})
    assert res.status_code == 422
    print("[PASS] Incomplete channel recording correctly rejected with 422.")

    # 4. Empty payload
    res = client.post("/api/analyze")
    assert res.status_code == 400
    print("[PASS] Empty payload correctly rejected with 400.")

if __name__ == "__main__":
    test_health()
    test_dataset_info()
    test_samples()
    test_model_evaluation()
    test_analysis_with_sample()
    test_invalid_upload_handling()
    print("\nALL 6 BACKEND AUTOMATED TEST SUITES PASSED CLEANLY (100% SUCCESS)!")
