# MeetingNote

Offline meeting transcription and translation workstation for Windows 11.

MeetingNote is a local-first desktop tool for turning audio and video recordings into usable meeting materials. It supports offline transcription, full-document Chinese/English translation, summary generation, task tracking, history management, and export workflows — all with replaceable local models.

## Highlights

- Local ASR transcription
- Full-document Chinese ↔ English translation
- Summary generation in the original transcript language
- History and task management
- Export for transcript, translation, and bilingual content
- Local runtime layout designed for portability across machines

## Features

- Offline audio/video preprocessing with `ffmpeg`
- Replaceable local ASR models under `models/asr/*`
- Replaceable local GGUF LLM models under `models/llm/*.gguf`
- Background task queue for preprocessing, transcription, translation, and summarization
- Language-aware workflow:
  - detect transcript language first
  - offer translation direction accordingly
- UI language switch: English / Chinese
- Export actions in the Results tab:
  - Export Transcript
  - Export Translation
  - Export Bilingual

## Runtime Layout

All runtime dependencies and data stay inside the project root for easier migration and local management.

```text
.venv/                 Python virtual environment
tools/ffmpeg/bin/      ffmpeg.exe + ffprobe.exe
models/asr/            ASR model directories
models/llm/            GGUF model files
data/                  SQLite + records + exports


Quick Start
1. Create a virtual environment
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
2. Install runtime providers
.\.venv\Scripts\python.exe -m pip install funasr
.\.venv\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.19/llama_cpp_python-0.3.19-cp311-cp311-win_amd64.whl
3. Place ffmpeg binaries

Put ffmpeg.exe and ffprobe.exe into:

tools/ffmpeg/bin/
4. Prepare and check models
.\check_models.bat
.\prepare_models.bat

Current default models:

ASR: SenseVoiceSmall → models/asr/SenseVoiceSmall/
Translation / Summary: qwen2.5-3b-instruct-q4_k_m.gguf → models/llm/
5. Run the application
.\run_dev.bat
Common Scripts
run_dev.bat — start the desktop app
check_runtime.bat — verify Python packages, ffmpeg, and ffprobe
check_models.bat — detect local model readiness
prepare_models.bat — download missing default models
Development
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
GitHub Upload Notes

This repository is configured to avoid uploading local runtime artifacts, including:

.venv/
data/* except data/.gitkeep
models/* except models/.gitkeep
local ffmpeg binaries under tools/ffmpeg/bin/*

You can use one-command packaging before upload:

powershell -ExecutionPolicy Bypass -File .\tools\prepare_github_upload.ps1

See also: docs/github_upload.md

Project Structure
src/meeting_note/      Application source code
tests/                 Test suite
docs/                  PRD, architecture, setup, and upload docs
assets/                Static assets
tools/                 Local helper scripts
models/                Local models (gitignored, with .gitkeep)
data/                  Runtime data (gitignored, with .gitkeep)
Design Goals

MeetingNote is built around a few practical goals:

keep sensitive meeting data local
make model components replaceable
support bilingual meeting workflows
provide structured export-ready outputs
keep deployment simple on Windows 11
Status

This project is currently under active local development and focuses on a Windows 11 offline workflow.
