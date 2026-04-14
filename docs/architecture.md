# Architecture Draft

## Recommended Stack

- Python 3.11 or 3.12
- PySide6 / Qt 6
- SQLite for indexes, tasks, model registry, and app settings
- JSON files for transcript, translation, and summary payloads
- ffmpeg for media preprocessing
- FunASR provider for Phase 1 ASR
- llama.cpp or llama-cpp-python provider for local GGUF LLM inference

## Modules

```text
ui/            Windows 11 desktop interface
core/          Audio, ASR, translation, summary, export, model settings, and task services
providers/     Pluggable ASR and LLM backends
data/          Repositories and schemas
infra/         Logging, diagnostics, configuration, packaging helpers
```

## Phase 1 Services

- AudioProcessor and PreprocessingService
- ASRService, ASRProviderFactory, and FunASRProvider
- LLMProviderFactory and LlamaCppProvider
- TranslationService and TranslationWorkflow
- SummaryService and SummaryWorkflow
- ExportService and ExportWorkflow
- ModelScanner and ModelSettingsService
- RecordRepository, ModelRepository, TaskRepository, and SettingsRepository
- TaskRunner for Qt background work

## Translation Principle

Translation is handled as a full-document workflow. The transcript segments are formatted into one complete source text and sent to the LLM in a single prompt so context, terminology, and meeting structure are preserved. Segment-by-segment translation is intentionally avoided.

## Runtime Data Layout

```text
data/
  database.sqlite
  records/
    {record_id}/
      audio.processed.wav
      transcript.json
      translation.json
      summary.json
      exports/
        transcript.txt
        translation.md
        bilingual.md
        summary.md
        subtitles.srt
  logs/
    app.log
models/
  asr/
    {asr_model_dir}/
  llm/
    {model}.gguf
```
