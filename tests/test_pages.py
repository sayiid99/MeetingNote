from __future__ import annotations

from pathlib import Path

from meeting_note.core.model_settings import ModelSelection
from meeting_note.data.models import (
    LocalModel,
    ModelProvider,
    ModelType,
    Record,
    RecordStatus,
    TaskRecord,
    TaskStatus,
    TaskType,
    now_utc,
)
from meeting_note.ui.history_page import HistoryPage
from meeting_note.ui.models_page import ModelsPage
from meeting_note.ui.settings_page import SettingsPage
from meeting_note.ui.tasks_page import TasksPage

def test_history_page_displays_records(qt_app):
    page = HistoryPage()
    record = Record(
        id="rec-1",
        title="Weekly Meeting",
        status=RecordStatus.READY,
        created_at=now_utc(),
        updated_at=now_utc(),
        has_transcript=True,
    )

    page.set_records([record])

    assert page.count() == 1


def test_models_page_displays_models(qt_app):
    page = ModelsPage()
    model = LocalModel(
        id="model-1",
        name="Qwen3 4B",
        path=Path("models/llm/qwen.gguf"),
        model_type=ModelType.LLM_TRANSLATION,
        provider=ModelProvider.LLAMA_CPP,
        file_size=1024 * 1024,
        quantization="Q4_K_M",
        created_at=now_utc(),
    )

    page.set_models([model])

    assert page.count() == 1


def test_settings_page_round_trips_model_selection(qt_app):
    page = SettingsPage()
    selection = ModelSelection(
        selected_asr_model_id="asr-1",
        selected_translation_model_id="translation-1",
        selected_summary_model_id="summary-1",
        llm_context_length=32768,
        llm_gpu_layers=16,
        llm_chat_format="chatml",
        llm_use_chat_completion=False,
    )

    page.set_model_selection(selection)

    assert page.model_selection() == selection


def test_history_page_emits_record_open_request(qt_app):
    page = HistoryPage()
    opened_record_ids: list[str] = []
    page.record_open_requested.connect(opened_record_ids.append)
    record = Record(
        id="rec-1",
        title="Weekly Meeting",
        status=RecordStatus.READY,
        created_at=now_utc(),
        updated_at=now_utc(),
        has_transcript=True,
    )
    page.set_records([record])

    page.open_record_at(0)

    assert opened_record_ids == ["rec-1"]


def test_settings_page_populates_model_options_by_type(qt_app):
    page = SettingsPage()
    models = [
        LocalModel(
            id="asr-1",
            name="SenseVoiceSmall",
            path=Path("models/asr/SenseVoiceSmall"),
            model_type=ModelType.ASR,
            provider=ModelProvider.FUNASR,
            created_at=now_utc(),
        ),
        LocalModel(
            id="translation-1",
            name="Qwen3 4B",
            path=Path("models/llm/qwen.gguf"),
            model_type=ModelType.LLM_TRANSLATION,
            provider=ModelProvider.LLAMA_CPP,
            created_at=now_utc(),
        ),
        LocalModel(
            id="summary-1",
            name="Qwen3 4B",
            path=Path("models/llm/qwen.gguf"),
            model_type=ModelType.LLM_SUMMARY,
            provider=ModelProvider.LLAMA_CPP,
            created_at=now_utc(),
        ),
    ]

    page.set_available_models(models)

    assert page.model_option_count(ModelType.ASR) == 1
    assert page.model_option_count(ModelType.LLM_TRANSLATION) == 1
    assert page.model_option_count(ModelType.LLM_SUMMARY) == 1


def test_settings_page_preserves_selection_when_models_refresh(qt_app):
    page = SettingsPage()
    selection = ModelSelection(
        selected_asr_model_id="asr-1",
        selected_translation_model_id="translation-1",
        selected_summary_model_id="summary-1",
        llm_context_length=32768,
    )
    page.set_model_selection(selection)

    page.set_available_models([])

    assert page.model_selection() == selection


def test_history_page_emits_action_requests_for_selected_record(qt_app):
    page = HistoryPage()
    emitted: dict[str, list[str]] = {
        "transcribe": [],
        "zh": [],
        "en": [],
    }
    page.record_transcribe_requested.connect(emitted["transcribe"].append)
    page.record_translate_to_chinese_requested.connect(emitted["zh"].append)
    page.record_translate_to_english_requested.connect(emitted["en"].append)
    records = [
        Record(
            id="rec-1",
            title="First",
            status=RecordStatus.READY,
            created_at=now_utc(),
            updated_at=now_utc(),
            processed_audio_path=Path("audio.wav"),
            has_transcript=True,
        ),
        Record(
            id="rec-2",
            title="Second",
            status=RecordStatus.READY,
            created_at=now_utc(),
            updated_at=now_utc(),
        ),
    ]
    page.set_records(records)

    page.transcribe_button.click()
    page.translate_to_chinese_button.click()
    page.translate_to_english_button.click()

    assert emitted == {
        "transcribe": ["rec-1"],
        "zh": ["rec-1"],
        "en": ["rec-1"],
    }


def test_history_page_clear_button_state_and_signal(qt_app):
    page = HistoryPage()
    emitted: list[bool] = []
    page.history_clear_requested.connect(lambda: emitted.append(True))
    assert page.clear_button.isEnabled() is False

    record = Record(
        id="rec-1",
        title="First",
        status=RecordStatus.READY,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    page.set_records([record])
    assert page.clear_button.isEnabled() is True

    page.clear_button.click()
    assert emitted == [True]

    page.set_records([])
    assert page.clear_button.isEnabled() is False




def test_tasks_page_displays_background_tasks(qt_app):
    page = TasksPage()
    task = TaskRecord(
        id="task-1",
        record_id="rec-1",
        task_type=TaskType.TRANSLATE,
        status=TaskStatus.RUNNING,
        progress=1,
        message="Translating full transcript",
    )

    page.set_tasks([task])

    assert page.count() == 1
    assert "translate | running | 1% | record rec-1" in page.task_text(0)
    assert "Translating full transcript" in page.task_text(0)
    assert page.clear_button.isEnabled() is True


def test_tasks_page_disables_clear_button_when_empty(qt_app):
    page = TasksPage()

    page.set_tasks([])

    assert page.count() == 0
    assert page.clear_button.isEnabled() is False


def test_history_page_disables_actions_for_missing_transcript_and_active_tasks(qt_app):
    page = HistoryPage()
    record = Record(
        id="rec-1",
        title="Weekly Meeting",
        status=RecordStatus.READY,
        created_at=now_utc(),
        updated_at=now_utc(),
        processed_audio_path=Path("audio.wav"),
        has_transcript=False,
    )
    page.set_records([record])

    assert page.open_button.isEnabled() is True
    assert page.transcribe_button.isEnabled() is True
    assert page.translate_to_chinese_button.isEnabled() is False
    assert page.translate_to_english_button.isEnabled() is False

    page.set_active_tasks(
        [
            TaskRecord(
                id="task-1",
                record_id="rec-1",
                task_type=TaskType.TRANSCRIBE,
                status=TaskStatus.RUNNING,
                progress=1,
            )
        ]
    )

    assert page.transcribe_button.isEnabled() is False



def test_history_page_shows_ready_hint_for_transcribed_record(qt_app):
    page = HistoryPage()
    record = Record(
        id="rec-1",
        title="Weekly Meeting",
        status=RecordStatus.READY,
        created_at=now_utc(),
        updated_at=now_utc(),
        processed_audio_path=Path("audio.wav"),
        has_transcript=True,
    )

    page.set_records([record])

    assert page.status_hint_text() == "Ready to open, transcribe, or translate this record."
    assert page.transcribe_button.text() == "Transcribe"
    assert page.translate_to_english_button.text() == "Translate to English"


def test_history_page_updates_hint_and_button_labels_for_active_translation(qt_app):
    page = HistoryPage()
    record = Record(
        id="rec-1",
        title="Weekly Meeting",
        status=RecordStatus.READY,
        created_at=now_utc(),
        updated_at=now_utc(),
        processed_audio_path=Path("audio.wav"),
        has_transcript=True,
    )
    page.set_records([record])

    page.set_active_tasks(
        [
            TaskRecord(
                id="task-1",
                record_id="rec-1",
                task_type=TaskType.TRANSLATE,
                status=TaskStatus.RUNNING,
                progress=1,
            )
        ]
    )

    assert page.status_hint_text() == "Translation is running for this record."
    assert page.translate_to_chinese_button.text() == "Translating..."
    assert page.translate_to_english_button.text() == "Translating..."
    assert page.translate_to_chinese_button.isEnabled() is False
    assert page.translate_to_english_button.isEnabled() is False
