@echo off
echo ========================================================
echo        NeuroScope - Launching Research Platform
echo ========================================================
echo.
echo Starting FastAPI Backend (Port 8000)...
start "NeuroScope Backend (FastAPI)" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 >nul

echo Starting React Frontend (Port 5173)...
start "NeuroScope Frontend (Vite)" cmd /k "cd frontend && npm run dev"

timeout /t 3 >nul

echo Opening browser at http://localhost:5173 ...
start http://localhost:5173

echo.
echo ========================================================
echo   NeuroScope is running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000/docs
echo ========================================================
