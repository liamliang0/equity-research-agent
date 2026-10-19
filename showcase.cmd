@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" showcase.py --valuation-input examples\valuation-assumptions.json
) else (
  python showcase.py --valuation-input examples\valuation-assumptions.json
)
if errorlevel 1 (
  echo Research did not complete. Existing public demo: docs\index.html
  pause
  exit /b 1
)
start "" "output\showcase\index.html"
pause
