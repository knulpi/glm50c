"""Terminal styling: ANSI colors and event glyphs, plain-text fallback.

Colors are enabled only on a TTY without NO_COLOR set; on Windows the
empty ``os.system("")`` call switches the console into VT mode. Everything
degrades to unstyled text automatically, so piped output stays clean.
"""

import os
import sys


def _supports_color() -> bool:
    if "NO_COLOR" in os.environ or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        # Constant empty string, no user input involved: this no-op shell
        # call is the documented trick to enable ANSI/VT processing in the
        # Windows console (safe alternative to a ctypes SetConsoleMode dance).
        os.system("")
    return True


ENABLED = _supports_color()

_RESET = "\033[0m"
_BOLD = "1"
_FAINT = "2"
_RED = "31"
_GREEN = "32"
_YELLOW = "33"
_BLUE = "34"
_MAGENTA = "35"
_CYAN = "36"


def paint(code: str, text: str) -> str:
    return f"\033[{code}m{text}{_RESET}" if ENABLED else text


def bold(text: str) -> str:
    return paint(_BOLD, text)


def faint(text: str) -> str:
    return paint(_FAINT, text)


def good(text: str) -> str:
    return paint(_GREEN, text)


def warn(text: str) -> str:
    return paint(_YELLOW, text)


def bad(text: str) -> str:
    return paint(_RED, text)


# One glyph + color per event kind; single-width characters only so
# columns stay aligned in every terminal.
GLYPHS = {
    "measurement": ("●", _GREEN),
    "partial": ("○", _GREEN),
    "area": ("▰", _BLUE),
    "volume": ("▣", _BLUE),
    "continuous": ("◐", _CYAN),
    "add": ("Σ", _YELLOW),
    "subtract": ("Σ", _YELLOW),
    "area_add": ("Σ", _YELLOW),
    "area_subtract": ("Σ", _YELLOW),
    "error": ("✗", _RED),
    "mode": ("→", _CYAN),
    "unknown": ("?", _MAGENTA),
}


def event_line(clock: str, kind: str, text: str) -> str:
    glyph, color = GLYPHS.get(kind, ("·", _FAINT))
    return f"{faint(clock)}  {paint(color, glyph)} {text}"


def clear_line() -> str:
    """Erase-to-end-of-line so a \\r status line leaves no stray characters."""
    return "\033[K" if ENABLED else ""
