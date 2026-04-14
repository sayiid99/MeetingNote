from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from meeting_note.core.model_settings import ModelSelection
from meeting_note.data.models import LocalModel, ModelType
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, UI_LANGUAGES, language_display_options, normalize_language, translate


class SettingsPage(QWidget):
    save_requested = Signal(object)
    reset_requested = Signal()

    def __init__(self, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._language = normalize_language(language)
        self._available_models: list[LocalModel] = []
        self._form_labels: dict[str, QLabel] = {}
        self._setup_ui()
        self.set_model_selection(ModelSelection(ui_language=self._language))

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._interface_language = QComboBox()
        self._interface_language.setEditable(False)
        self._populate_interface_language_combo()

        self._asr_model_id = self._create_model_combo()
        self._translation_model_id = self._create_model_combo()
        self._summary_model_id = self._create_model_combo()
        self._context_length = QSpinBox()
        self._context_length.setRange(1024, 262144)
        self._context_length.setSingleStep(1024)
        self._gpu_layers = QSpinBox()
        self._gpu_layers.setRange(-1, 999)
        self._chat_format = QLineEdit()
        self._use_chat_completion = QCheckBox()

        self._add_form_row(form, "settings.interface_language", self._interface_language)
        self._add_form_row(form, "settings.asr_model", self._asr_model_id)
        self._add_form_row(form, "settings.translation_model", self._translation_model_id)
        self._add_form_row(form, "settings.summary_model", self._summary_model_id)
        self._add_form_row(form, "settings.context_length", self._context_length)
        self._add_form_row(form, "settings.gpu_layers", self._gpu_layers)
        self._add_form_row(form, "settings.chat_format", self._chat_format)
        self._add_form_row(form, "settings.chat_mode", self._use_chat_completion)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        self._save_button = QPushButton()
        self._reset_button = QPushButton()
        self._save_button.clicked.connect(self._emit_save_requested)
        self._reset_button.clicked.connect(self.reset_requested)
        button_row.addStretch(1)
        button_row.addWidget(self._reset_button)
        button_row.addWidget(self._save_button)
        layout.addLayout(button_row)
        layout.addStretch(1)
        self._retranslate_ui()

    @property
    def save_button(self) -> QPushButton:
        return self._save_button

    @property
    def reset_button(self) -> QPushButton:
        return self._reset_button

    def set_language(self, language: str) -> None:
        normalized = normalize_language(language)
        if normalized == self._language:
            return
        self._language = normalized
        self._retranslate_ui()
        if self._available_models:
            self.set_available_models(self._available_models)

    def set_available_models(self, models: list[LocalModel]) -> None:
        current_selection = self.model_selection()
        self._available_models = models
        self._populate_model_combo(self._asr_model_id, models, ModelType.ASR)
        self._populate_model_combo(self._translation_model_id, models, ModelType.LLM_TRANSLATION)
        self._populate_model_combo(self._summary_model_id, models, ModelType.LLM_SUMMARY)
        self.set_model_selection(current_selection)

    def set_model_selection(self, selection: ModelSelection) -> None:
        self._set_combo_model_id(self._asr_model_id, selection.selected_asr_model_id)
        self._set_combo_model_id(self._translation_model_id, selection.selected_translation_model_id)
        self._set_combo_model_id(self._summary_model_id, selection.selected_summary_model_id)
        self._set_ui_language(selection.ui_language)
        self._context_length.setValue(selection.llm_context_length)
        self._gpu_layers.setValue(selection.llm_gpu_layers)
        self._chat_format.setText(selection.llm_chat_format or "")
        self._use_chat_completion.setChecked(selection.llm_use_chat_completion)

    def model_selection(self) -> ModelSelection:
        return ModelSelection(
            selected_asr_model_id=self._optional_combo_text(self._asr_model_id),
            selected_translation_model_id=self._optional_combo_text(self._translation_model_id),
            selected_summary_model_id=self._optional_combo_text(self._summary_model_id),
            ui_language=self._selected_ui_language(),
            llm_context_length=self._context_length.value(),
            llm_gpu_layers=self._gpu_layers.value(),
            llm_chat_format=self._optional_text(self._chat_format),
            llm_use_chat_completion=self._use_chat_completion.isChecked(),
        )

    def model_option_count(self, model_type: ModelType) -> int:
        combo = {
            ModelType.ASR: self._asr_model_id,
            ModelType.LLM_TRANSLATION: self._translation_model_id,
            ModelType.LLM_SUMMARY: self._summary_model_id,
        }[model_type]
        return max(0, combo.count() - 1)

    def _add_form_row(self, form: QFormLayout, key: str, field: QWidget) -> None:
        label = QLabel()
        form.addRow(label, field)
        self._form_labels[key] = label

    def _emit_save_requested(self) -> None:
        self.save_requested.emit(self.model_selection())

    @staticmethod
    def _create_model_combo() -> QComboBox:
        combo = QComboBox()
        combo.setEditable(False)
        return combo

    def _populate_model_combo(self, combo: QComboBox, models: list[LocalModel], model_type: ModelType) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(self._tr("settings.auto_select"), "")
        for model in models:
            if model.model_type != model_type:
                continue
            combo.addItem(self._model_label(model), model.id)
        combo.blockSignals(False)

    @staticmethod
    def _model_label(model: LocalModel) -> str:
        if model.quantization:
            return f"{model.name} [{model.quantization}]"
        return model.name

    def _set_combo_model_id(self, combo: QComboBox, model_id: str | None) -> None:
        if not model_id:
            combo.setCurrentIndex(0)
            return

        index = combo.findData(model_id)
        if index < 0:
            combo.addItem(self._tr("settings.unavailable", model_id=model_id), model_id)
            index = combo.count() - 1
        combo.setCurrentIndex(index)

    @staticmethod
    def _optional_combo_text(combo: QComboBox) -> str | None:
        data = combo.currentData()
        if isinstance(data, str) and data.strip():
            return data.strip()
        return None

    @staticmethod
    def _optional_text(line_edit: QLineEdit) -> str | None:
        text = line_edit.text().strip()
        return text or None

    def _populate_interface_language_combo(self) -> None:
        selected = self._selected_ui_language()
        options = language_display_options(self._language)
        self._interface_language.blockSignals(True)
        self._interface_language.clear()
        for language_code in UI_LANGUAGES:
            self._interface_language.addItem(options[language_code], language_code)
        self._interface_language.blockSignals(False)
        self._set_ui_language(selected)

    def _set_ui_language(self, language: str | None) -> None:
        normalized = normalize_language(language)
        index = self._interface_language.findData(normalized)
        if index < 0:
            index = self._interface_language.findData(DEFAULT_UI_LANGUAGE)
        self._interface_language.setCurrentIndex(max(index, 0))

    def _selected_ui_language(self) -> str:
        selected = self._interface_language.currentData()
        if isinstance(selected, str) and selected.strip():
            return normalize_language(selected)
        return DEFAULT_UI_LANGUAGE

    def _retranslate_ui(self) -> None:
        for key, label in self._form_labels.items():
            label.setText(self._tr(key))
        self._use_chat_completion.setText(self._tr("settings.use_chat_completion"))
        self._save_button.setText(self._tr("settings.save"))
        self._reset_button.setText(self._tr("settings.reset"))
        self._populate_interface_language_combo()

    def _tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)
