import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.app.database import get_db
from backend.app.models_db import AnalysisHistory, User
from backend.app.schemas import HistoryItem
from backend.app.utils.pdf_generator import generate_pdf_report
from backend.app.utils.auth import get_current_user_optional

router = APIRouter(prefix="/api", tags=["Reports"])

@router.get("/history", response_model=List[HistoryItem])
def get_history(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve previous analysis records from SQLite (user-specific when authenticated)."""
    query = db.query(AnalysisHistory)
    if current_user:
        query = query.filter(AnalysisHistory.user_id == current_user.id)
    else:
        query = query.filter(AnalysisHistory.user_id.is_(None))
    records = query.order_by(AnalysisHistory.created_at.desc()).limit(100).all()
    results = []
    for r in records:
        results.append(HistoryItem(
            id=r.id,
            user_id=r.user_id,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "N/A",
            filename=r.filename,
            original_label=r.original_label,
            predicted_class=r.predicted_class,
            confidence_score=r.confidence_score,
            prob_msa=r.prob_msa,
            prob_pd=r.prob_pd,
            knn_baseline=r.knn_baseline,
            is_uncertain=r.is_uncertain,
            duration_sec=r.duration_sec
        ))
    return results

@router.get("/history/{analysis_id}")
def get_history_detail(analysis_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve detailed information about a past analysis."""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    return {
        "id": record.id,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "N/A",
        "filename": record.filename,
        "original_label": record.original_label,
        "person_id": record.person_id,
        "trial_id": record.trial_id,
        "duration_sec": record.duration_sec,
        "sampling_rate_hz": record.sampling_rate_hz,
        "predicted_class": record.predicted_class,
        "confidence_score": record.confidence_score,
        "prob_msa": record.prob_msa,
        "prob_pd": record.prob_pd,
        "knn_baseline": record.knn_baseline,
        "is_uncertain": record.is_uncertain,
        "uncertainty_reasons": json.loads(record.uncertainty_reasons_json or "[]"),
        "top_shap_features": json.loads(record.top_shap_json or "[]"),
        "extracted_features": json.loads(record.extracted_features_json or "{}"),
        "notes": record.notes
    }

@router.delete("/history/{analysis_id}")
def delete_history_item(analysis_id: int, db: Session = Depends(get_db)):
    """Delete an analysis record from SQLite."""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")
    db.delete(record)
    db.commit()
    return {"status": "success", "message": f"Deleted record {analysis_id}"}

@router.get("/reports/{analysis_id}/pdf")
def download_pdf_report(analysis_id: int, db: Session = Depends(get_db)):
    """Generate and download a comprehensive research PDF report for the given analysis."""
    record = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    analysis_data = {
        "prediction": {
            "predicted_class": record.predicted_class,
            "confidence_score": record.confidence_score,
            "probabilities": {
                "MSA": record.prob_msa,
                "PD": record.prob_pd
            },
            "knn_baseline_class": record.knn_baseline,
            "is_uncertain": record.is_uncertain,
            "uncertainty_reasons": json.loads(record.uncertainty_reasons_json or "[]")
        },
        "input_metadata": {
            "filename": record.filename,
            "original_label": record.original_label,
            "person_id": record.person_id,
            "trial_id": record.trial_id,
            "duration_sec": record.duration_sec,
            "sampling_rate_hz": record.sampling_rate_hz
        },
        "shap_explanation": {
            "top_features": json.loads(record.top_shap_json or "[]")
        },
        "extracted_features": json.loads(record.extracted_features_json or "{}")
    }

    pdf_buffer = generate_pdf_report(analysis_data)
    filename = f"NeuroKinematix_Report_{record.predicted_class}_{record.id}.pdf"
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
