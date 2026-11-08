@echo off
cd /d %~dp0frontend
echo Starting EDITH Frontend on http://127.0.0.1:5500 ...
python -m http.server 5500
pause
