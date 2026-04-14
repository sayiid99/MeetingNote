@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Create it with: python -m venv .venv
  pause
  exit /b 1
)

if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" (
  set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
)

set "PYTHONPATH=%~dp0src"

echo [Python]
"%~dp0.venv\Scripts\python.exe" --version
if errorlevel 1 goto :fail

echo.
echo [Runtime imports]
"%~dp0.venv\Scripts\python.exe" -c "import PySide6, funasr, llama_cpp, torch, torchaudio; print('PySide6', PySide6.__version__); print('funasr', getattr(funasr, '__version__', 'unknown')); print('llama_cpp', getattr(llama_cpp, '__version__', 'unknown')); print('torch', torch.__version__); print('torchaudio', torchaudio.__version__)"
if errorlevel 1 goto :fail

echo.
echo [ffmpeg]
"%~dp0tools\ffmpeg\bin\ffmpeg.exe" -version
if errorlevel 1 goto :fail

echo.
echo [ffprobe]
"%~dp0tools\ffmpeg\bin\ffprobe.exe" -version
if errorlevel 1 goto :fail

echo.
echo [OK] Runtime is ready.
exit /b 0

:fail
echo.
echo [ERROR] Runtime check failed.
exit /b 1
