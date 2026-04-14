from __future__ import annotations

from pathlib import Path

from meeting_note.core.app_controller import AppController
from meeting_note.core.contracts import Language, TranscriptDocument, TranscriptSegment
from meeting_note.core.model_scanner import ModelScanner
from meeting_note.data.database import initialize_database
from meeting_note.data.document_store import TranscriptStore, TranslationStore
from meeting_note.data.repositories import ModelRepository, RecordRepository
from meeting_note.infra.paths import AppPaths
from meeting_note.ui.main_window import MainWindow


class FakeASRProvider:
    def transcribe(self, audio_path: Path, source_language: Language) -> TranscriptDocument:
        return TranscriptDocument(
            record_id=audio_path.stem,
            language=source_language,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )


class FakeASRProviderFactory:
    def create_provider(self) -> FakeASRProvider:
        return FakeASRProvider()


class FakeLLMProvider:
    def generate(self, prompt: str, *, max_tokens: int | None = None) -> str:
        return "Full translation."


class FakeLLMProviderFactory:
    def create_translation_provider(self) -> FakeLLMProvider:
        return FakeLLMProvider()


def test_models_page_shows_missing_status_when_project_has_no_models(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    window = MainWindow(paths)
    AppController(
        window=window,
        record_repository=RecordRepository(paths.database_path),
        model_repository=ModelRepository(paths.database_path),
        model_scanner=ModelScanner(paths.models_dir),
    )

    assert "ASR: missing" in window.models_page.status_text()
    assert "Translation: missing" in window.models_page.status_text()


def test_app_controller_blocks_transcription_when_no_project_asr_model(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    processed_audio_path = paths.processed_audio_path(record.id)
    processed_audio_path.parent.mkdir(parents=True)
    processed_audio_path.write_bytes(b"processed")
    repository.mark_preprocessed(record.id, processed_audio_path)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        model_repository=ModelRepository(paths.database_path),
        model_scanner=ModelScanner(paths.models_dir),
        asr_provider_factory=FakeASRProviderFactory(),
        transcript_store=TranscriptStore(paths),
    )

    transcript = controller.transcribe_record(record.id, Language.ENGLISH)

    assert transcript is None
    assert window.statusBar().currentMessage() == "No ASR model found. Open Models and run Prepare Recommended Models."


def test_app_controller_blocks_translation_when_no_project_gguf_model(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        model_repository=ModelRepository(paths.database_path),
        model_scanner=ModelScanner(paths.models_dir),
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
    )

    translation = controller.translate_record(record.id, Language.ENGLISH)

    assert translation is None
    assert window.statusBar().currentMessage() == "No GGUF translation model found. Open Models and run Prepare Recommended Models."


def test_app_controller_uses_detected_project_models_for_translation(qt_app, tmp_path):
    paths = AppPaths.from_project_root(tmp_path)
    paths.ensure_runtime_dirs()
    initialize_database(paths.database_path)
    llm_dir = paths.models_dir / "llm"
    llm_dir.mkdir(parents=True)
    (llm_dir / "qwen2.5-3b-instruct-q4_k_m.gguf").write_bytes(b"fake gguf")
    repository = RecordRepository(paths.database_path)
    record = repository.create_record("demo")
    transcript_store = TranscriptStore(paths)
    translation_store = TranslationStore(paths)
    transcript_store.save(
        TranscriptDocument(
            record_id=record.id,
            language=Language.CHINESE,
            segments=[TranscriptSegment(id="seg-1", text="Hello", start_time=0, end_time=1)],
        )
    )
    repository.mark_transcript_ready(record.id, Path("processed.wav"), "zh", has_speakers=False)
    window = MainWindow(paths)
    controller = AppController(
        window=window,
        record_repository=repository,
        model_repository=ModelRepository(paths.database_path),
        model_scanner=ModelScanner(paths.models_dir),
        llm_provider_factory=FakeLLMProviderFactory(),
        transcript_store=transcript_store,
        translation_store=translation_store,
        run_model_tasks_in_background=False,
    )

    translation = controller.translate_record(record.id, Language.ENGLISH)

    assert translation is not None
    assert translation.translated_text == "Full translation."
