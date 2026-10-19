@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" showcase.py --watchlist watchlist.case.example.json --case-profile examples\avgo-case-profile.json --company-profiles examples\memory-company-profiles.json --output output\public-case
) else (
  python showcase.py --watchlist watchlist.case.example.json --case-profile examples\avgo-case-profile.json --company-profiles examples\memory-company-profiles.json --output output\public-case
)
if errorlevel 1 (
  echo Research did not complete. Existing public case: docs\index.html
  pause
  exit /b 1
)
start "" "output\public-case\index.html"
pause
