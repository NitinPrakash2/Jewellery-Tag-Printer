@echo off
REM Daily use: double-click this file. The app opens for the whole shop WiFi.
REM First time only: run setup-first-time.bat once (it creates everything).
REM Optional, once, as Administrator: allow-lan.ps1 (lets other laptops in).

cd /d "%~dp0"
set CORS_ORIGINS=*
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
