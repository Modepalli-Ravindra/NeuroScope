import os
import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from backend.app.database import get_db
from backend.app.models_db import AnalysisHistory, User
from backend.app.schemas import AnalysisResponse
from backend.ml.inference import InferenceEngine
from backend.app.routers.dataset import get_real_sample_by_id, DATA_DIR
from backend.app.utils.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["Analysis"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_recording(
    file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Execute complete screening inference and SHAP explanation pipeline.
    Accepts either an uploaded .mat file or a verified sample_id from real dataset.
    Persists research result into SQLite.
    """
    engine = InferenceEngine.get_instance()
    filename = "upload.mat"
    content = None
    sample_meta = None

    if sample_id:
        sample_meta = get_real_sample_by_id(sample_id)
        if not sample_meta:
            raise HTTPException(status_code=404, detail=f"Recording '{sample_id}' not found in dataset repository.")
        
        sample_path = os.path.join(DATA_DIR, sample_meta["rel_path"])
        if not os.path.exists(sample_path):
            raise HTTPException(status_code=404, detail=f"Recording file not found on disk: {sample_meta['rel_path']}")
            
        with open(sample_path, "rb") as f:
            content = f.read()
        filename = sample_meta["filename"]

    elif file:
        if not file.filename.lower().endswith(".mat"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a MATLAB .mat recording containing 6 gyroscope channels.")
        content = await file.read()
        filename = file.filename
        if len(content) < 500:
            raise HTTPException(status_code=400, detail="Uploaded file is too small or empty.")

    else:
        raise HTTPException(status_code=400, detail="Either a .mat file upload or a sample_id must be provided.")

    # 1. Parse MAT data
    try:
        parsed_data = engine.parse_mat_bytes(content, filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process movement recording: {str(e)}")

    # 2. Run Inference & SHAP explanation
    try:
        result = engine.predict(parsed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    # 3. Save into SQLite
    try:
        pred = result["prediction"]
        meta = result["input_metadata"]
        db_record = AnalysisHistory(
            user_id=current_user.id if current_user else None,
            filename=filename,
            original_label=meta.get("original_label", "UNKNOWN"),
            person_id=meta.get("person_id", "ANONYMOUS"),
            trial_id=meta.get("trial_id", "trial1"),
            duration_sec=meta.get("duration_sec", 0.0),
            sampling_rate_hz=meta.get("sampling_rate_hz", 200.0),
            predicted_class=pred["predicted_class"],
            confidence_score=pred["confidence_score"],
            prob_msa=pred["probabilities"]["MSA"],
            prob_pd=pred["probabilities"]["PD"],
            knn_baseline=pred["knn_baseline_class"],
            is_uncertain=pred["is_uncertain"],
            uncertainty_reasons_json=json.dumps(pred["uncertainty_reasons"]),
            top_shap_json=json.dumps(result["shap_explanation"]["top_features"]),
            extracted_features_json=json.dumps(result["extracted_features"]),
            model_version=result["model_metadata"]["model_version"],
            notes=notes or ""
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        result["id"] = db_record.id
    except Exception as e:
        print(f"Warning: Failed to save to database: {e}")
        result["id"] = None

    return result

@router.get("/explain/{analysis_id}")
def get_analysis_explanation(analysis_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve stored SHAP explanation and feature breakdown for an existing analysis."""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    return {
        "id": record.id,
        "filename": record.filename,
        "predicted_class": record.predicted_class,
        "confidence_score": record.confidence_score,
        "prob_msa": record.prob_msa,
        "prob_pd": record.prob_pd,
        "knn_baseline": record.knn_baseline,
        "top_shap_features": json.loads(record.top_shap_json or "[]"),
        "is_uncertain": record.is_uncertain,
        "uncertainty_reasons": json.loads(record.uncertainty_reasons_json or "[]"),
        "extracted_features": json.loads(record.extracted_features_json or "{}")
    }
