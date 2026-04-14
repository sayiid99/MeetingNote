# GitHub Upload Guide

This document is for preparing a clean GitHub upload package from local development workspace.

## Why Packaging

Your local workspace may contain:
- local models
- local database and export results
- local ffmpeg binaries
- local virtual environment

These files are machine-specific and should not be committed to GitHub.

## One-Command Packaging

From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\prepare_github_upload.ps1
```

Output:
- `dist/MeetingNote-github-YYYYMMDD_HHMMSS.zip`

## What Is Excluded

- `.venv/`
- `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`
- `data/` runtime files
- `models/` model files
- `tools/ffmpeg/` local binaries
- common local DB files (`*.db`, `*.sqlite`, `*.sqlite3`)
- Python cache files (`__pycache__`, `*.pyc`)

The package keeps placeholders:
- `data/.gitkeep`
- `models/.gitkeep`
- `tools/ffmpeg/bin/.gitkeep`

## Optional Parameters

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\prepare_github_upload.ps1 -KeepStaging
```

Use `-KeepStaging` if you want to inspect the staging folder before uploading.

## Suggested Upload Flow

1. Generate package with the script.
2. Unzip to a new clean folder.
3. Initialize Git repository in that clean folder.
4. Review content once (`README.md`, `docs/`, `src/`, `tests/`).
5. Push to GitHub.
