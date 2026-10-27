import os
import pickle
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/api/voice", tags=["Voice (Experimental)"])

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "saved_models")
VOICE_MODEL_PATH = os.path.join(MODELS_DIR, "best_pd_voice_model.pkl")

# Load reused reference model if available
voice_model_data = None
try:
    if os.path.exists(VOICE_MODEL_PATH):
        with open(VOICE_MODEL_PATH, "rb") as f:
            voice_model_data = pickle.load(f)
except Exception as e:
    print(f"Notice: Voice model load skipped ({e})")

@router.get("/info")
def get_voice_module_info() -> Dict[str, Any]:
    """Information on the optional experimental PD voice screening module."""
    return {
        "status": "available" if voice_model_data is not None else "unavailable",
        "description": "Optional experimental voice screening module reused from Parkinson's-Disease-Voice-Detector (MIT License).",
        "target_task": "Parkinson's Disease vs. Healthy Voice (Binary)",
        "critical_distinction": "This module detects Parkinsonian voice changes versus healthy controls. It DOES NOT perform MSA vs PD differential screening. Movement sensor models must be used for MSA differentiation.",
        "features_used": voice_model_data.get("selected_features", []) if voice_model_data else []
    }
