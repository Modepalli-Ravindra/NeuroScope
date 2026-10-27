@echo off
title NeuroScope — Explainable AI Movement Screening
echo =====================================================================
echo           NEUROSCOPE: MSA vs. Parkinson's Disease Screening
echo               B.Tech Mini-Project - Local Runtime Launcher
echo =====================================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.12+ and add to PATH.
    pause
    exit /b 1
)

:: 2. Check Node
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not found in PATH. Please install Node.js (v18+) and add to PATH.
    pause
    exit /b 1
)

:: 3. Check if model artifact exists, if not run training
if not exist "backend\saved_models\neuroscope_rf_model.joblib" (
    echo [INFO] Model artifacts not found. Initiating one-time training on authentic dataset...
    python -m backend.ml.train_models
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Model training failed.
        pause
        exit /b 1
    )
)

echo [1/2] Starting NeuroScope FastAPI Backend on http://127.0.0.1:8000 ...
start "NeuroScope Backend" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

echo [2/2] Starting NeuroScope React Frontend on http://127.0.0.1:5173 ...
cd frontend
start "NeuroScope Frontend" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"
cd ..

echo.
echo =====================================================================
echo  NeuroScope is now running!
echo  - Frontend Dashboard: http://127.0.0.1:5173
echo  - Backend API Docs:   http://127.0.0.1:8000/docs
echo =====================================================================
echo.
pause
