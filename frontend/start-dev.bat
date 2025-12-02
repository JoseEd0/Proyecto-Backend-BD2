@echo off
echo.
echo ========================================
echo   BD2 Manager - Development Setup
echo ========================================
echo.

cd /d "%~dp0"

if not exist "node_modules" (
    echo [1/3] Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
) else (
    echo [1/3] Dependencies already installed
    echo.
)

echo [2/3] Checking backend...
cd ..
if exist "api\main.py" (
    echo Backend found at api\main.py
    echo.
) else (
    echo WARNING: Backend not found. Make sure to start it separately.
    echo.
)

cd frontend

echo [3/3] Starting frontend development server...
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000 (start separately)
echo.
echo Press Ctrl+C to stop
echo.

call npm run dev
