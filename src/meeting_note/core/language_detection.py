from __future__ import annotations

import re

from meeting_note.core.contracts import Language


def detect_primary_language(text: str, default: Language = Language.ENGLISH) -> Language:
    chinese_count, latin_count = _character_counts(text)
    if chinese_count == 0 and latin_count == 0:
        return default
    return Language.CHINESE if chinese_count >= latin_count else Language.ENGLISH


def is_text_in_language(text: str, target_language: Language) -> bool:
    chinese_count, latin_count = _character_counts(text)
    if chinese_count == 0 and latin_count == 0:
        return False

    total = chinese_count + latin_count
    if target_language == Language.CHINESE:
        if chinese_count == 0:
            return False
        if latin_count == 0:
            return True
        return (chinese_count / total) >= 0.45

    if target_language == Language.ENGLISH:
        if latin_count == 0:
            return False
        if chinese_count == 0:
            return True
        return (latin_count / total) >= 0.60

    return False


def _character_counts(text: str) -> tuple[int, int]:
    chinese_count = len(re.findall(r"[\u3400-\u9FFF]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    return chinese_count, latin_count
