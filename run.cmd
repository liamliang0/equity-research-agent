@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe research_agent.py %*
) else (
  py -3 research_agent.py %*
)
if errorlevel 1 (echo 研究未成功，旧报告保留。 & pause & exit /b 1)
if exist output\latest-ai-report.html start "" "%~dp0output\latest-ai-report.html"
