from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from meeting_note.core.media import SUPPORTED_AUDIO_FORMATS, SUPPORTED_VIDEO_FORMATS, qt_file_dialog_filter, validate_media_file
from meeting_note.ui.i18n import DEFAULT_UI_LANGUAGE, normalize_language, translate


class UploadPage(QWidget):
    media_selected = Signal(str)

    def __init__(self, language: str = DEFAULT_UI_LANGUAGE):
        super().__init__()
        self._language = normalize_language(language)
        self._selected_path: Path | None = None
        self._status_kind: str = "supported"
        self._status_error: tuple[str, object | None] | None = None
        self.setAcceptDrops(True)
        self._setup_ui()

    @property
    def selected_path(self) -> Path | None:
        return self._selected_path

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(self._title_label)

        self._hint_label = QLabel()
        self._hint_label.setAlignment(Qt.AlignCenter)
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._choose_button = QPushButton()
        self._choose_button.setFixedWidth(180)
        self._choose_button.clicked.connect(self._choose_file)
        layout.addWidget(self._choose_button, alignment=Qt.AlignCenter)
        self._retranslate_ui()

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self._retranslate_ui()

    def _choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("upload.dialog_title"),
            "",
            qt_file_dialog_filter(),
        )
        if file_path:
            self.handle_file(Path(file_path))

    def handle_file(self, file_path: Path) -> bool:
        try:
            media_file = validate_media_file(file_path)
        except (FileNotFoundError, ValueError) as exc:
            self._selected_path = None
            self._status_kind = "error"
            if isinstance(exc, FileNotFoundError):
                self._status_error = ("not_found", file_path)
            else:
                suffix = file_path.suffix or ""
                supported = ", ".join(sorted(SUPPORTED_AUDIO_FORMATS | SUPPORTED_VIDEO_FORMATS))
                self._status_error = ("unsupported", (suffix, supported))
            self._apply_status_text()
            self._status_label.setStyleSheet("color: #c62828;")
            return False

        self._selected_path = media_file.path
        self._status_kind = "selected"
        self._status_error = None
        self._apply_status_text()
        self._status_label.setStyleSheet("color: #2e7d32;")
        self.media_selected.emit(str(media_file.path))
        return True

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _retranslate_ui(self) -> None:
        self._title_label.setText(self._tr("upload.title"))
        self._hint_label.setText(self._tr("upload.hint"))
        self._apply_status_text()
        if self._status_kind == "supported":
            self._status_label.setStyleSheet("")
        self._choose_button.setText(self._tr("upload.choose_file"))

    def _tr(self, key: str, **kwargs: object) -> str:
        return translate(self._language, key, **kwargs)

    def _apply_status_text(self) -> None:
        if self._status_kind == "error" and self._status_error:
            error_type, payload = self._status_error
            if error_type == "not_found" and isinstance(payload, Path):
                text = (
                    self._tr("upload.error.not_found", path=payload)
                    if self._language == "en"
                    else f"媒体文件不存在：{payload}"
                )
            elif error_type == "unsupported" and isinstance(payload, tuple):
                suffix, supported = payload
                if self._language == "en":
                    text = self._tr("upload.error.unsupported", suffix=suffix, supported=supported)
                else:
                    text = f"不支持的媒体格式：{suffix}。支持的格式：{supported}"
            else:
                text = self._tr("upload.supported")
            self._status_label.setText(text)
            return

        if self._status_kind == "selected" and self._selected_path is not None:
            self._status_label.setText(self._tr("upload.selected", name=self._selected_path.name))
            return

        self._status_label.setText(self._tr("upload.supported"))

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        local_file = urls[0].toLocalFile()
        if local_file:
            self.handle_file(Path(local_file))
            event.acceptProposedAction()
        else:
            event.ignore()
