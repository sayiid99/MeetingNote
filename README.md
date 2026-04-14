# MeetingNote

Offline meeting transcription and translation workstation for Windows 11.

MeetingNote focuses on local-first workflow:
- Local ASR transcription
- Full-document Chinese/English translation (not sentence-by-sentence)
- Summary generation in the source transcript language
- History and task management
- Export for transcript/translation/bilingual content

## Features

- Offline audio/video preprocessing (`ffmpeg`)
- Replaceable local ASR models (`models/asr/*`)
- Replaceable local GGUF LLM models (`models/llm/*.gguf`)
- Background task queue for preprocess/transcribe/translate
- Language-aware workflow:
  - detect transcript language first
  - then offer translation direction accordingly
- UI language switch (English / Chinese)
- Export buttons in Results tab:
  - Export Transcript
  - Export Translation
  - Export Bilingual

## Runtime Layout (Project-Local)

```text
.venv/                 Python virtual environment
tools/ffmpeg/bin/      ffmpeg.exe + ffprobe.exe
models/asr/            ASR model directories
models/llm/            GGUF model files
data/                  SQLite + records + exports
```

Everything above stays inside project root, so the project is easier to migrate to another machine.

## Quick Start

### 1) Create venv

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 2) Install runtime providers

```powershell
.\.venv\Scripts\python.exe -m pip install funasr
.\.venv\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.19/llama_cpp_python-0.3.19-cp311-cp311-win_amd64.whl
```

### 3) Place ffmpeg

Put `ffmpeg.exe` and `ffprobe.exe` into:

```text
tools/ffmpeg/bin/
```

### 4) Prepare/check models

```powershell
.\check_models.bat
.\prepare_models.bat
```

Current default models:
- ASR: `SenseVoiceSmall` -> `models/asr/SenseVoiceSmall/`
- Translation/Summary: `qwen2.5-3b-instruct-q4_k_m.gguf` -> `models/llm/`

### 5) Run

```powershell
.\run_dev.bat
```

## Common Scripts

- `run_dev.bat`: start desktop app
- `check_runtime.bat`: verify Python packages + ffmpeg/ffprobe
- `check_models.bat`: detect local model readiness
- `prepare_models.bat`: download missing default models

## Development

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

## Upload To GitHub

This repo is configured to avoid uploading local runtime artifacts:
- `.venv/`
- `data/*` (except `data/.gitkeep`)
- `models/*` (except `models/.gitkeep`)
- local ffmpeg binaries under `tools/ffmpeg/bin/*`

You can use one-command packaging:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\prepare_github_upload.ps1
```

Packaging notes: [docs/github_upload.md](docs/github_upload.md)

## Project Structure

```text
src/meeting_note/      Application source code
tests/                 Test suite
docs/                  PRD, architecture, setup and upload docs
assets/                Static assets
tools/                 Local helper scripts
models/                Local models (gitignored, with .gitkeep)
data/                  Runtime data (gitignored, with .gitkeep)
```
