@echo off
cd /d %~dp0
if not exist .env copy .env.example .env
echo Starting EDITH-TRIP MANAGER API on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
