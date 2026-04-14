from __future__ import annotations

from dataclasses import dataclass

from meeting_note.data.repositories import SettingsRepository


@dataclass(frozen=True)
class ModelSelection:
    selected_asr_model_id: str | None = None
    selected_translation_model_id: str | None = None
    selected_summary_model_id: str | None = None
    ui_language: str = "en"
    llm_context_length: int = 8192
    llm_gpu_layers: int = -1
    llm_chat_format: str | None = None
    llm_use_chat_completion: bool = True


class ModelSettingsService:
    KEY_ASR_MODEL_ID = "selected_asr_model_id"
    KEY_TRANSLATION_MODEL_ID = "selected_translation_model_id"
    KEY_SUMMARY_MODEL_ID = "selected_summary_model_id"
    KEY_UI_LANGUAGE = "ui_language"
    KEY_LLM_CONTEXT_LENGTH = "llm_context_length"
    KEY_LLM_GPU_LAYERS = "llm_gpu_layers"
    KEY_LLM_CHAT_FORMAT = "llm_chat_format"
    KEY_LLM_USE_CHAT_COMPLETION = "llm_use_chat_completion"

    def __init__(self, settings_repository: SettingsRepository):
        self._settings_repository = settings_repository

    def load(self) -> ModelSelection:
        ui_language = self._settings_repository.get(self.KEY_UI_LANGUAGE, "en") or "en"
        normalized_ui_language = "zh" if ui_language.strip().lower().startswith("zh") else "en"
        return ModelSelection(
            selected_asr_model_id=self._settings_repository.get(self.KEY_ASR_MODEL_ID),
            selected_translation_model_id=self._settings_repository.get(self.KEY_TRANSLATION_MODEL_ID),
            selected_summary_model_id=self._settings_repository.get(self.KEY_SUMMARY_MODEL_ID),
            ui_language=normalized_ui_language,
            llm_context_length=self._settings_repository.get_int(self.KEY_LLM_CONTEXT_LENGTH, 8192),
            llm_gpu_layers=self._settings_repository.get_int(self.KEY_LLM_GPU_LAYERS, -1),
            llm_chat_format=self._settings_repository.get(self.KEY_LLM_CHAT_FORMAT),
            llm_use_chat_completion=self._settings_repository.get_bool(
                self.KEY_LLM_USE_CHAT_COMPLETION,
                True,
            ),
        )

    def save(self, selection: ModelSelection) -> None:
        normalized_ui_language = "zh" if selection.ui_language.strip().lower().startswith("zh") else "en"
        self._settings_repository.set_many(
            {
                self.KEY_ASR_MODEL_ID: selection.selected_asr_model_id,
                self.KEY_TRANSLATION_MODEL_ID: selection.selected_translation_model_id,
                self.KEY_SUMMARY_MODEL_ID: selection.selected_summary_model_id,
                self.KEY_UI_LANGUAGE: normalized_ui_language,
                self.KEY_LLM_CONTEXT_LENGTH: selection.llm_context_length,
                self.KEY_LLM_GPU_LAYERS: selection.llm_gpu_layers,
                self.KEY_LLM_CHAT_FORMAT: selection.llm_chat_format,
                self.KEY_LLM_USE_CHAT_COMPLETION: selection.llm_use_chat_completion,
            }
        )
