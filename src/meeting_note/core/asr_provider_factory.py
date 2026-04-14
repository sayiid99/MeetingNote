from __future__ import annotations

import logging

from meeting_note.core.contracts import ASRProvider
from meeting_note.core.model_settings import ModelSettingsService
from meeting_note.data.models import LocalModel, ModelType
from meeting_note.data.repositories import ModelRepository
from meeting_note.providers.funasr_provider import FunASRProvider

logger = logging.getLogger(__name__)


class ASRProviderFactory:
    def __init__(
        self,
        *,
        model_repository: ModelRepository,
        model_settings_service: ModelSettingsService,
        device: str = "cpu",
        enable_speakers: bool = True,
    ):
        self._model_repository = model_repository
        self._model_settings_service = model_settings_service
        self._device = device
        self._enable_speakers = enable_speakers

    def create_provider(self) -> ASRProvider:
        selection = self._model_settings_service.load()
        model = self._select_model(selection.selected_asr_model_id)
        return FunASRProvider(
            models_dir=model.path.parent,
            device=self._device,
            enable_speakers=self._enable_speakers,
            asr_model_dir=model.path,
        )

    def _select_model(self, selected_model_id: str | None) -> LocalModel:
        models = self._model_repository.list_models(ModelType.ASR)
        if not models:
            raise ValueError("No ASR model is available. Scan or add a FunASR model directory first.")

        if selected_model_id:
            selected = self._find_model(models, selected_model_id)
            if selected is not None:
                return selected
            logger.warning(
                "Selected ASR model is not available: %s. Falling back to first detected model %s.",
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
