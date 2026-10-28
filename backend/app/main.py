import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base
from backend.app.routers import dataset, models, analysis, reports, voice, auth
from backend.ml.inference import InferenceEngine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NeuroScope API — Explainable MSA vs. PD Screening",
    description="Educational AI research backend for differential screening of Multiple System Atrophy and Parkinson's Disease.",
    version="1.0.0"
)

# Enable CORS for local React/Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(dataset.router)
app.include_router(models.router)
app.include_router(analysis.router)
app.include_router(reports.router)
app.include_router(voice.router)

@app.on_event("startup")
def startup_event():
    # Warm up inference engine so models and SHAP explainer are loaded
    InferenceEngine.get_instance()
    print("NeuroScope FastAPI server started and ready for inference.")

@app.get("/health")
@app.get("/api/health")
def health_check():
    engine_inst = InferenceEngine.get_instance()
    return {
        "status": "healthy",
        "service": "NeuroScope Backend",
        "version": "3.0.0",
        "primary_model": "Optimized Logistic Regression v3.0 (92.58% Balanced Accuracy, 27 LOPO-CV Folds)",
        "models_loaded": {
            "primary_v3": engine_inst.v3_available,
            "random_forest": engine_inst.rf_model is not None,
            "knn_baseline": engine_inst.knn_model is not None,
            "linear_shap_explainer": engine_inst.v3_available
        },
        "features_loaded": len(engine_inst.feature_cols)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
