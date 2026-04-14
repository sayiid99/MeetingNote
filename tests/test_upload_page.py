from __future__ import annotations

from meeting_note.ui.upload_page import UploadPage


def test_upload_page_accepts_supported_existing_file(qt_app, tmp_path):
    page = UploadPage()
    audio_file = tmp_path / "meeting.wav"
    audio_file.write_bytes(b"fake")

    assert page.handle_file(audio_file) is True
    assert page.selected_path == audio_file


def test_upload_page_rejects_unsupported_file(qt_app, tmp_path):
    page = UploadPage()
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not media", encoding="utf-8")

    assert page.handle_file(text_file) is False
    assert page.selected_path is None
