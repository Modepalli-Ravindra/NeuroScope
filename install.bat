@echo off
echo ========================================================
echo        NeuroScope - Automated Setup and Install
echo ========================================================
echo.

echo [1/2] Installing Python Backend Dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies. Please check Python installation.
    pause
    exit /b %errorlevel%
)
echo [SUCCESS] Backend dependencies installed.
echo.

echo [2/2] Installing Frontend Node.js Dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install npm dependencies. Please check Node.js installation.
    pause
    exit /b %errorlevel%
)
cd ..
echo [SUCCESS] Frontend dependencies installed.
echo.

echo ========================================================
echo   Setup Complete! Double click 'start.bat' to launch.
echo ========================================================
pause
