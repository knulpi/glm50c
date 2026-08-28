"""Language selection: 'de' or 'en', autodetected from the locale by default."""

import locale
import os

from glm50c.lang import de, en

LANGUAGES = {"de": de, "en": en}


def detect() -> str:
    lang = locale.getlocale()[0] or os.environ.get("LANG") or ""
    return "de" if lang.lower().startswith("de") else "en"


def get_language(code: str | None = None):
    """Return the language module for `code`, or autodetect (fallback: en)."""
    return LANGUAGES[code if code in LANGUAGES else detect()]
