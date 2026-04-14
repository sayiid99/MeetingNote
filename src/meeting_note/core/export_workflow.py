from __future__ import annotations

from pathlib import Path

from meeting_note.core.contracts import TranscriptDocument, TranslationDocument
from meeting_note.core.export_service import ExportService
from meeting_note.core.formatting import format_transcript_document
from meeting_note.data.document_store import SummaryStore, TranscriptStore, TranslationStore
from meeting_note.infra.paths import AppPaths


class ExportWorkflow:
    SUPPORTED_DOCUMENT_FORMATS = {"txt", "md", "docx", "pdf"}

    def __init__(
        self,
        *,
        paths: AppPaths,
        export_service: ExportService,
        transcript_store: TranscriptStore,
        translation_store: TranslationStore,
        summary_store: SummaryStore,
    ):
        self._paths = paths
        self._export_service = export_service
        self._transcript_store = transcript_store
        self._translation_store = translation_store
        self._summary_store = summary_store

    def export_transcript(self, record_id: str, document_format: str = "txt") -> Path:
        transcript = self._require_transcript(record_id)
        content = format_transcript_document(transcript)
        output_path = self._output_path(record_id, "transcript", document_format)
        if self._normalize_format(document_format) == "txt":
            return self._export_service.export_transcript_txt(transcript, output_path)
        return self._export_content("Transcript", content, output_path, document_format)

    def export_translation(self, record_id: str, document_format: str = "txt") -> Path:
        translation = self._require_translation(record_id)
        output_path = self._output_path(record_id, "translation", document_format)
        if self._normalize_format(document_format) == "txt":
            return self._export_service.export_translation_txt(translation, output_path)
        return self._export_content("Translation", translation.translated_text, output_path, document_format)

    def export_bilingual(self, record_id: str, document_format: str = "md") -> Path:
        translation = self._require_translation(record_id)
        content = translation.bilingual_text or translation.translated_text
        output_path = self._output_path(record_id, "bilingual", document_format)
        return self._export_content("Bilingual Transcript", content, output_path, document_format)

    def export_summary(self, record_id: str, document_format: str = "md") -> Path:
        summary = self._require_summary(record_id)
        output_path = self._output_path(record_id, "summary", document_format)
        return self._export_content("Summary", summary, output_path, document_format)

    def export_srt(self, record_id: str, *, show_speakers: bool = True) -> Path:
        transcript = self._require_transcript(record_id)
        output_path = self._paths.exports_dir(record_id) / "subtitles.srt"
        return self._export_service.export_srt(transcript, output_path, show_speakers=show_speakers)

    def _export_content(self, title: str, content: str, output_path: Path, document_format: str) -> Path:
        normalized_format = self._normalize_format(document_format)
        match normalized_format:
            case "txt":
                return self._export_service.export_text(content, output_path)
            case "md":
                return self._export_service.export_markdown(title, content, output_path)
            case "docx":
                return self._export_service.export_docx(title, content, output_path)
            case "pdf":
                return self._export_service.export_pdf(title, content, output_path)
            case _:
                raise ValueError(f"Unsupported export format: {document_format}")

    def _output_path(self, record_id: str, stem: str, document_format: str) -> Path:
        return self._paths.exports_dir(record_id) / f"{stem}.{self._normalize_format(document_format)}"

    def _require_transcript(self, record_id: str) -> TranscriptDocument:
        transcript = self._transcript_store.load(record_id)
        if transcript is None:
            raise ValueError(f"Transcript is not available for record {record_id}.")
        return transcript

    def _require_translation(self, record_id: str) -> TranslationDocument:
        translation = self._translation_store.load(record_id)
        if translation is None:
            raise ValueError(f"Translation is not available for record {record_id}.")
        return translation

    def _require_summary(self, record_id: str) -> str:
        summary = self._summary_store.load(record_id)
        if summary is None:
            raise ValueError(f"Summary is not available for record {record_id}.")
        return summary

    @classmethod
    def _normalize_format(cls, document_format: str) -> str:
        normalized_format = document_format.lower().lstrip(".")
        if normalized_format == "markdown":
            normalized_format = "md"
        if normalized_format not in cls.SUPPORTED_DOCUMENT_FORMATS:
            raise ValueError(f"Unsupported export format: {document_format}")
        return normalized_format
