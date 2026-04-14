from __future__ import annotations

from meeting_note.core.contracts import (
    Language,
    TranscriptDocument,
    TranscriptSegment,
    TranslationDocument,
    TranslationMode,
)
from meeting_note.ui.results_page import ResultsPage


def test_results_page_displays_transcript(qt_app):
    page = ResultsPage()
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.ENGLISH,
        segments=[TranscriptSegment(id="1", text="Start", start_time=1, end_time=2, speaker_id="S1")],
    )

    page.display_transcript(transcript)

    assert "S1" in page.transcript_text()
    assert "Start" in page.transcript_text()


def test_results_page_displays_translation_and_bilingual_text(qt_app):
    page = ResultsPage()
    translation = TranslationDocument(
        record_id="rec-1",
        source_language=Language.CHINESE,
        target_language=Language.ENGLISH,
        mode=TranslationMode.STANDARD,
        translated_text="Full translation.",
        bilingual_text="Source\n\nFull translation.",
    )

    page.display_translation(translation)

    assert page.translation_text() == "Full translation."
    assert page.bilingual_text() == "Source\n\nFull translation."


def test_results_page_sets_summary_text_without_switching(qt_app):
    page = ResultsPage()

    page.set_summary_text("Summary content")

    assert page.summary_text() == "Summary content"


def test_results_page_sets_translation_text_without_switching(qt_app):
    page = ResultsPage()

    page.set_translation_text("Translated", "Source\n\nTranslated")

    assert page.translation_text() == "Translated"
    assert page.bilingual_text() == "Source\n\nTranslated"


def test_results_page_clears_all_text(qt_app):
    page = ResultsPage()
    transcript = TranscriptDocument(
        record_id="rec-1",
        language=Language.ENGLISH,
        segments=[TranscriptSegment(id="1", text="Start", start_time=1, end_time=2, speaker_id="S1")],
    )
    translation = TranslationDocument(
        record_id="rec-1",
        source_language=Language.ENGLISH,
        target_language=Language.CHINESE,
        mode=TranslationMode.STANDARD,
        translated_text="翻译",
        bilingual_text="Start\n\n翻译",
    )
    page.display_transcript(transcript)
    page.display_translation(translation)
    page.set_summary_text("Summary")

    page.clear_results()

    assert page.transcript_text() == ""
    assert page.translation_text() == ""
    assert page.bilingual_text() == ""
    assert page.summary_text() == ""


def test_results_page_emits_export_requests(qt_app):
    page = ResultsPage()
    emitted: list[str] = []
    page.export_transcript_requested.connect(lambda: emitted.append("transcript"))
    page.export_translation_requested.connect(lambda: emitted.append("translation"))
    page.export_bilingual_requested.connect(lambda: emitted.append("bilingual"))

    page.export_transcript_button.click()
    page.export_translation_button.click()
    page.export_bilingual_button.click()

    assert emitted == ["transcript", "translation", "bilingual"]
