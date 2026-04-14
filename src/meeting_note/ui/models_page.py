from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meeting_note.core.model_preparation import ModelAvailabilitySummary
from meeting_note.data.models import LocalModel
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, normalize_language, translate


class ModelsPage(QWidget):
    def __init__(self, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._language = normalize_language(language)
        self._models: list[LocalModel] = []
        self._latest_summary: ModelAvailabilitySummary | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self._title_label)

        self._hint_label = QLabel()
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        actions = QHBoxLayout()
        self._prepare_button = QPushButton()
        self._open_folder_button = QPushButton()
        self._refresh_button = QPushButton()
        actions.addWidget(self._prepare_button)
        actions.addWidget(self._open_folder_button)
        actions.addWidget(self._refresh_button)
        layout.addLayout(actions)

        self._list = QListWidget()
        layout.addWidget(self._list)
        self._retranslate_ui()

    @property
    def prepare_button(self) -> QPushButton:
        return self._prepare_button

    @property
    def open_folder_button(self) -> QPushButton:
        return self._open_folder_button

    @property
    def refresh_button(self) -> QPushButton:
        return self._refresh_button

    def set_models(self, models: list[LocalModel]) -> None:
        self._models = list(models)
        self._list.clear()
        for model in models:
            item = QListWidgetItem(self._format_model(model))
            item.setData(256, model.id)
            self._list.addItem(item)

    def set_model_availability(self, summary: ModelAvailabilitySummary) -> None:
        self._latest_summary = summary
        self._status_label.setText("\n".join(self._format_model_availability(summary)))

    def count(self) -> int:
        return self._list.count()

    def status_text(self) -> str:
        return self._status_label.text()

    def _format_model(self, model: LocalModel) -> str:
        size_mb = model.file_size / 1024 / 1024 if model.file_size else 0
        quantization = model.quantization or ("未知量化" if self._language == "zh" else "unknown quant")
        model_type = self._model_type_label(model.model_type.value)
        return f"{model.name}\n{model_type} | {quantization} | {size_mb:.1f} MB"

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self._retranslate_ui()
        if self._models:
            self.set_models(self._models)
        if self._latest_summary is not None:
            self.set_model_availability(self._latest_summary)

    def _retranslate_ui(self) -> None:
        self._title_label.setText(self._tr("models.title"))
        self._hint_label.setText(self._tr("models.hint"))
        if not self._status_label.text().strip():
            self._status_label.setText(self._tr("models.status_scan"))
        self._prepare_button.setText(self._tr("models.prepare"))
        self._open_folder_button.setText(self._tr("models.open_folder"))
        self._refresh_button.setText(self._tr("models.scan"))

    def _tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)

    def _format_model_availability(self, summary: ModelAvailabilitySummary) -> list[str]:
        lines = [
            self._summary_line(self._summary_label("asr"), summary.asr_ready, summary.asr_count),
            self._summary_line(self._summary_label("translation"), summary.translation_ready, summary.translation_count),
            self._summary_line(self._summary_label("summary"), summary.summary_ready, summary.summary_count),
        ]
        missing = summary.missing_required()
        if missing:
            lines.append(self._tr("models.summary.missing_defaults"))
            for spec in missing:
                target = spec.target_path(self._models_dir_hint())
                lines.append(f"- {spec.label} -> {target} ({spec.download_size_hint})")
        else:
            lines.append(self._tr("models.summary.core_ready"))
        return lines

    def _summary_line(self, label: str, ready: bool, count: int) -> str:
        status = self._tr("models.summary.ready" if ready else "models.summary.missing")
        detected = self._tr("models.summary.detected", count=count)
        return f"{label}: {status} ({detected})"

    def _summary_label(self, kind: str) -> str:
        if self._language == "zh":
            return {
                "asr": "ASR",
                "translation": "翻译",
                "summary": "摘要",
            }.get(kind, kind)
        return {
            "asr": "ASR",
            "translation": "Translation",
            "summary": "Summary",
        }.get(kind, kind)

    def _model_type_label(self, model_type: str) -> str:
        if self._language == "zh":
            return {
                "asr": "ASR",
                "llm_translation": "翻译模型",
                "llm_summary": "摘要模型",
            }.get(model_type, model_type)
        return {
            "asr": "ASR",
            "llm_translation": "Translation model",
            "llm_summary": "Summary model",
        }.get(model_type, model_type)

    def _models_dir_hint(self):
        # Relative labels keep the UI copy clean; the actual folder is shown elsewhere.
        from pathlib import Path

        return Path("models")
