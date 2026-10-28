@echo off
cd /d "%~dp0"
echo ========================================================
echo        NeuroScope - Launching Research Platform
echo ========================================================
echo.

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm was not found!
    echo NeuroScope React Frontend requires Node.js.
    echo Please install Node.js (LTS version) from:
    echo   https://nodejs.org/
    echo After installing, rerun start.bat.
    pause
    exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
    echo [INFO] First-time setup: Installing frontend dependencies...
    cd /d "%~dp0frontend"
    call npm install
    cd /d "%~dp0"
)

echo Starting FastAPI Backend (Port 8000)...
start "NeuroScope Backend (FastAPI)" /d "%~dp0" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 >nul

echo Starting React Frontend (Port 5173)...
start "NeuroScope Frontend (Vite)" /d "%~dp0frontend" cmd /k "npm run dev"

timeout /t 3 >nul

echo Opening browser at http://localhost:5173 ...
start http://localhost:5173

echo.
echo ========================================================
echo   NeuroScope is running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000/docs
echo ========================================================

