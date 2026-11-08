@echo off
setlocal

REM ==============================================================================
REM EcoMind - Sustainability-Aware AI Inference Control Plane
REM Unified Local Launcher (Windows)
REM ==============================================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo ==============================================================================
echo                      EcoMind Control Plane - Local Launcher
echo ==============================================================================
echo Project Directory: %PROJECT_ROOT%
echo.

REM ------------------------------------------------------------------------------
REM Step 1: Validate Global System Prerequisites (Python, Node.js, npm)
REM ------------------------------------------------------------------------------
echo [1/4] Checking system prerequisites...

where python >nul 2>&1
if errorlevel 1 goto :err_no_python

where node >nul 2>&1
if errorlevel 1 goto :err_no_node

where npm >nul 2>&1
if errorlevel 1 goto :err_no_npm

echo   [OK] Python, Node.js, and npm are available in PATH.
echo.

REM ------------------------------------------------------------------------------
REM Step 2: Validate Backend Virtual Environment & Dependencies
REM ------------------------------------------------------------------------------
echo [2/4] Validating backend environment and dependencies...

if not exist "%PROJECT_ROOT%backend\venv\Scripts\python.exe" goto :err_no_venv
if not exist "%PROJECT_ROOT%backend\venv\Scripts\uvicorn.exe" goto :err_no_uvicorn

if not exist "%PROJECT_ROOT%backend\.env" (
    echo   [WARNING] backend\.env configuration file was not found.
    echo             Copy backend\.env.example to backend\.env to configure API keys.
) else (
    echo   [OK] backend\.env configuration file found.
)

echo   [OK] Backend virtual environment and uvicorn are verified.
echo.

REM ------------------------------------------------------------------------------
REM Step 3: Validate Frontend Dependencies
REM ------------------------------------------------------------------------------
echo [3/4] Validating frontend environment and dependencies...

if not exist "%PROJECT_ROOT%frontend\node_modules" goto :err_no_nodemodules

echo   [OK] Frontend node_modules directory is present.
echo.

REM ------------------------------------------------------------------------------
REM Step 4: Check for Running Port Conflicts (8000 & 5173)
REM ------------------------------------------------------------------------------
echo [4/4] Checking network ports (Backend: 8000, Frontend: 5173)...

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo   [WARNING] Port 8000 is currently in use. An existing backend process may be active.
) else (
    echo   [OK] Port 8000 is free.
)

netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo   [WARNING] Port 5173 is currently in use. An existing frontend dev server may be active.
) else (
    echo   [OK] Port 5173 is free.
)
echo.

REM ------------------------------------------------------------------------------
REM Launch Services in Dedicated Terminal Windows
REM ------------------------------------------------------------------------------
echo ==============================================================================
echo                      Starting EcoMind Services...
echo ==============================================================================
echo   Backend API:        http://127.0.0.1:8000
echo   API Documentation:  http://127.0.0.1:8000/docs
echo   Frontend Dashboard: http://localhost:5173
echo.
echo   Press Ctrl+C in either service window to stop that component.
echo   Close both windows to fully terminate EcoMind.
echo ==============================================================================
echo.

start "EcoMind Backend (FastAPI - Port 8000)" cmd /k "title EcoMind Backend (FastAPI) && cd /d "%PROJECT_ROOT%backend" && call "venv\Scripts\activate.bat" && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

start "EcoMind Frontend (Vite - Port 5173)" cmd /k "title EcoMind Frontend (Vite) && cd /d "%PROJECT_ROOT%frontend" && npm run dev"

echo Both services have been launched in separate terminal windows.
echo You can monitor logs and inspect errors directly in their respective windows.
echo.
exit /b 0

:err_no_python
echo [ERROR] Python is not installed or not found in system PATH.
echo.
echo Resolution:
echo   1. Download and install Python 3.10+ from: https://www.python.org/downloads/
echo   2. Ensure "Add Python to PATH" is checked during installation.
echo   3. Restart your terminal or command prompt.
echo.
pause
exit /b 1

:err_no_node
echo [ERROR] Node.js is not installed or not found in system PATH.
echo.
echo Resolution:
echo   1. Download and install Node.js (LTS v18+) from: https://nodejs.org/
echo   2. Restart your terminal or command prompt.
echo.
pause
exit /b 1

:err_no_npm
echo [ERROR] npm is not installed or not found in system PATH.
echo.
echo Resolution:
echo   1. Ensure npm is bundled with your Node.js installation.
echo   2. Add the npm bin directory to your system PATH.
echo.
pause
exit /b 1

:err_no_venv
echo [ERROR] Backend Python virtual environment not found at:
echo         %PROJECT_ROOT%backend\venv
echo.
echo Resolution:
echo   1. Open a terminal and navigate to the backend directory:
echo        cd backend
echo   2. Create the virtual environment:
echo        python -m venv venv
echo   3. Activate the environment:
echo        venv\Scripts\activate.bat
echo   4. Install the backend dependencies:
echo        pip install -r requirements.txt
echo.
pause
exit /b 1

:err_no_uvicorn
echo [ERROR] uvicorn is not installed in the backend virtual environment.
echo.
echo Resolution:
echo   1. Activate the backend virtual environment:
echo        cd backend
echo        venv\Scripts\activate.bat
echo   2. Install backend dependencies:
echo        pip install -r requirements.txt
echo.
pause
exit /b 1

:err_no_nodemodules
echo [ERROR] Frontend node_modules directory not found at:
echo         %PROJECT_ROOT%frontend\node_modules
echo.
echo Resolution:
echo   1. Open a terminal and navigate to the frontend directory:
echo        cd frontend
echo   2. Install the frontend dependencies:
echo        npm install
echo.
pause
exit /b 1
