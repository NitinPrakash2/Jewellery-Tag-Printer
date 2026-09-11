@echo off
setlocal DisableDelayedExpansion
title Jewellery Tag Printer - First Time Setup (one time only)
cd /d "%~dp0"

echo ============================================================
echo  Jewellery Tag Printer - First Time Setup
echo  (Run ONCE on the shop computer. 5-10 minutes.)
echo ============================================================
echo.

echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo   Python NOT found. Install from https://www.python.org/downloads/
  echo   IMPORTANT: tick "Add python.exe to PATH" during install, then re-run this file.
  pause
  exit /b 1
)
echo   OK.

echo [2/6] Checking PostgreSQL...
psql --version >nul 2>&1
if errorlevel 1 (
  echo   PostgreSQL NOT found. Install from https://www.postgresql.org/download/windows/
  echo   Note the password you set during install, then re-run this file.
  pause
  exit /b 1
)
echo   OK.

echo [3/6] Installing server libraries (internet needed once)...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo   Library install failed. Check internet and re-run.
  pause
  exit /b 1
)

echo [4/6] Creating database...
echo   TIP: keep the password simple letters-numbers. Avoid  ^& ^< ^> ^| ^^  characters.
set /p PGPASS=Enter your PostgreSQL password (you set it during install):
set PGPASSWORD=%PGPASS%
psql -U postgres -h localhost -d postgres -c "CREATE DATABASE jewellery_tags;" 2>nul
echo   Done (if it already existed, that is fine).

echo [5/6] Writing config + database tables...
(
echo DATABASE_URL=postgresql+psycopg2://postgres:%PGPASS%@localhost:5432/jewellery_tags
echo APP_ENV=prod
echo LOG_LEVEL=INFO
echo CORS_ORIGINS=*
) > .env
echo   NOTE: if your password has  #  replace it with %%23 in the .env file,
echo   and if it has  @  replace it with %%40.
set DATABASE_URL=postgresql+psycopg2://postgres:%PGPASS%@localhost:5432/jewellery_tags
python -m alembic upgrade head
if errorlevel 1 (
  echo   Database tables failed. Fix the password in .env and re-run.
  pause
  exit /b 1
)

echo [6/6] Building the app screen...
where node >nul 2>&1
if errorlevel 1 (
  echo   Node.js NOT found - install from https://nodejs.org/ then re-run. Skipping build for now.
) else (
  cd /d "%~dp0..\client"
  call npm install
  call npm run build
  cd /d "%~dp0"
)

echo.
echo ============================================================
echo  SETUP COMPLETE!
echo  Daily use: double-click start-lan.bat
echo  Then open the address it shows from any laptop on the WiFi.
echo  First print: Settings -^> Run Setup -^> Test Print.
echo ============================================================
pause
