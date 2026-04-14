from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from meeting_note.core.contracts import LLMProvider
from meeting_note.core.model_settings import ModelSettingsService, ModelSelection
from meeting_note.data.models import LocalModel, ModelType
from meeting_note.data.repositories import ModelRepository
from meeting_note.providers.llama_cpp_provider import LlamaCppConfig, LlamaCppProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    def __init__(
        self,
        *,
        model_repository: ModelRepository,
        model_settings_service: ModelSettingsService,
        llama_factory: Callable[..., Any] | None = None,
    ):
        self._model_repository = model_repository
        self._model_settings_service = model_settings_service
        self._llama_factory = llama_factory

    def create_translation_provider(self) -> LLMProvider:
        selection = self._model_settings_service.load()
        model = self._select_model(ModelType.LLM_TRANSLATION, selection.selected_translation_model_id)
        return self._create_llama_provider(model, selection)

    def create_summary_provider(self) -> LLMProvider:
        selection = self._model_settings_service.load()
        model = self._select_model(ModelType.LLM_SUMMARY, selection.selected_summary_model_id)
        return self._create_llama_provider(model, selection)

    def _select_model(self, model_type: ModelType, selected_model_id: str | None) -> LocalModel:
        models = self._model_repository.list_models(model_type)
        if not models:
            raise ValueError(f"No {model_type.value} model is available. Scan or add a GGUF model first.")

        if selected_model_id:
            selected = self._find_model(models, selected_model_id)
            if selected is not None:
                return selected
            logger.warning(
                "Selected %s model is not available: %s. Falling back to first detected model %s.",
                model_type.value,
                selected_model_id,
                models[0].id,
            )
        return models[0]

    @staticmethod
    def _find_model(models: list[LocalModel], selected_model_id: str) -> LocalModel | None:
        normalized = selected_model_id.strip().lower()
        if not normalized:
            return None

        for model in models:
            if model.id.lower() == normalized:
                return model

        for model in models:
            aliases = {
                model.name.lower(),
                model.path.name.lower(),
                model.path.stem.lower(),
            }
            if normalized in aliases:
                return model
        return None

    def _create_llama_provider(self, model: LocalModel, selection: ModelSelection) -> LlamaCppProvider:
        return LlamaCppProvider(
            model_path=model.path,
            config=LlamaCppConfig(
                n_ctx=selection.llm_context_length,
                n_gpu_layers=selection.llm_gpu_layers,
                chat_format=selection.llm_chat_format,
                use_chat_completion=selection.llm_use_chat_completion,
            ),
            llama_factory=self._llama_factory,
        )
