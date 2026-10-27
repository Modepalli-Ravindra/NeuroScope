# NeuroScope PowerShell Launcher
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          NEUROSCOPE: MSA vs. Parkinson's Disease Screening          " -ForegroundColor White
Write-Host "              B.Tech Mini-Project - Local Runtime Launcher           " -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan

# 1. Verify model artifacts
$modelPath = "backend\saved_models\neuroscope_rf_model.joblib"
if (-not (Test-Path $modelPath)) {
    Write-Host "[INFO] Training models on authentic finger-tapping dataset..." -ForegroundColor Yellow
    python -m backend.ml.train_models
}

# 2. Launch Backend
Write-Host "[1/2] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

# 3. Launch Frontend
Write-Host "[2/2] Launching React + Vite Frontend on http://127.0.0.1:5173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev -- --host 127.0.0.1 --port 5173"

Write-Host ""
Write-Host "NeuroScope is launching!" -ForegroundColor Green
Write-Host "  -> Frontend: http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  -> Backend Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host ""
