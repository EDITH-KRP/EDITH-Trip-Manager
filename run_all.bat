@echo off
cd /d %~dp0
echo ===================================================
echo   EDITH-TRIP MANAGER - Starting Backend and Frontend
echo ===================================================
echo.
if not exist .env copy .env.example .env

echo [1/2] Launching Backend API server (port 8000)...
start "EDITH Backend API (FastAPI)" cmd /k "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Launching Frontend Web server (port 5500)...
start "EDITH Frontend (Web)" cmd /k "cd frontend && python -m http.server 5500"

echo.
echo Waiting for services to initialize...
ping 127.0.0.1 -n 3 >nul

echo Opening browser at http://127.0.0.1:5500 ...
start http://127.0.0.1:5500

echo.
echo Both servers have been launched in separate console windows.
echo Keep those command windows open while using the app.
