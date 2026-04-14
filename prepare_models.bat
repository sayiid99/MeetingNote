@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Create it with: python -m venv .venv
  pause
  exit /b 1
)

set "PYTHONPATH=%~dp0src"
"%~dp0.venv\Scripts\python.exe" -m meeting_note.model_manager prepare
pause
