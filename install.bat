@echo off
cd /d "%~dp0"
echo ========================================================
echo        NeuroScope - Automated Setup and Install
echo ========================================================
echo.

echo [Checking Prerequisites]
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python (3.10 to 3.13) and check "Add Python to PATH".
    pause
    exit /b 1
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm is NOT installed on your computer!
    echo NeuroScope React Frontend requires Node.js.
    echo Download and install Node.js (LTS version) from:
    echo   https://nodejs.org/
    echo After installing, restart your terminal and run install.bat again.
    pause
    exit /b 1
)

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
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install npm dependencies.
    pause
    exit /b %errorlevel%
)
cd /d "%~dp0"
echo [SUCCESS] Frontend dependencies installed.
echo.

echo ========================================================
echo   Setup Complete! Double click 'start.bat' to launch.
echo ========================================================
pause

