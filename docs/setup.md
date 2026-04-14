# Local Setup

## Goal

Keep the runnable environment and model files inside the project folder so the app can be moved or handed over with less external setup.

## Current Local Runtime

The following runtime pieces are expected to live under the project root:

```text
.venv/                 Python virtual environment
tools/ffmpeg/bin/      ffmpeg.exe and ffprobe.exe
models/asr/            Offline ASR model folders
models/llm/            Offline GGUF model files
data/                  Local database and generated outputs
```

## Requirements

- Windows 11
- Python 3.11
- Enough disk space for local models and runtime packages
- Optional: larger replacement GGUF models after first boot

## Create Local Environment

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Install Runtime Providers

Use the local virtual environment inside the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install funasr
.\.venv\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.19/llama_cpp_python-0.3.19-cp311-cp311-win_amd64.whl
```

Notes:

- `funasr` is used for offline transcription.
- `llama-cpp-python` is installed from a prebuilt Windows wheel to avoid a local C++ build toolchain requirement.
- `torch` and `torchaudio` are installed from the CPU index for a simpler Windows 11 local runtime.
- The project-local model preparation flow uses `modelscope`, which is already brought in by the ASR runtime.

## Add Local ffmpeg

Copy `ffmpeg.exe` and `ffprobe.exe` into `tools/ffmpeg/bin/`.

The launcher and runtime check scripts already prefer this local folder automatically.

## Check and Prepare Models

Use these project-local entry points:

```powershell
.\check_models.bat
.\prepare_models.bat
```

Current default downloads:

- `SenseVoiceSmall` -> `models/asr/SenseVoiceSmall/`
- `qwen2.5-3b-instruct-q4_k_m.gguf` -> `models/llm/`

The app checks for usable local models before transcription or translation. If a required category is missing, it will tell you to open the Models tab and run the preparation flow.

## Place Local Models Manually

You can also place models manually.

ASR models are scanned from directories under `models/asr/`:

```text
models/asr/SenseVoiceSmall/
models/asr/YourOtherASRModel/
```

LLM models are scanned from GGUF files under `models/llm/`:

```text
models/llm/qwen2.5-3b-instruct-q4_k_m.gguf
models/llm/YourOtherModel.gguf
```

Use the Settings tab to save selected model IDs and llama.cpp parameters such as context length, GPU layers, chat format, and chat-completion mode.

## Verify Runtime

```powershell
.\check_runtime.bat
```

This checks:

- Python in `.venv`
- PySide6
- FunASR
- llama.cpp Python binding
- torch and torchaudio
- local `ffmpeg.exe`
- local `ffprobe.exe`

## Run Quality Checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

## Run App

```powershell
.\run_dev.bat
```

The Phase 1 shell currently opens tabs for New, Results, History, Models, and Settings. The transcription and translation workflows are available through the controller layer and are ready to be used with project-local models.
