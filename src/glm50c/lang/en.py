"""English announcements and console strings.

Number verbalization mirrors the structure of the German module but speaks
decimals digit by digit ("one point eight four three meters"), which is the
natural English style and keeps the function pure and testable.
"""

NAME = "en"
DEFAULT_VOICE = "en_US-lessac-medium"

MODES = {1.0: "Length", 2.0: "Continuous", 4.0: "Area", 7.0: "Volume"}

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty",
        "seventy", "eighty", "ninety"]

_ORDINALS = {1: "First", 2: "Second", 3: "Third"}


def number_word(n: int) -> str:
    """0..99999 as an English number word ('eighty-four', 'two thousand one')."""
    if n >= 1000:
        t, r = divmod(n, 1000)
        return f"{number_word(t)} thousand" + (f" {number_word(r)}" if r else "")
    if n >= 100:
        h, r = divmod(n, 100)
        return f"{ONES[h]} hundred" + (f" {number_word(r)}" if r else "")
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    if o == 0:
        return TENS[t]
    return f"{TENS[t]}-{ONES[o]}"


def _digits_spoken(digits: str) -> str:
    return " ".join(ONES[int(d)] for d in digits)


def _quantity(whole: int, fraction_digits: str, singular: str, plural: str) -> str:
    """'one meter', 'two meters', 'one point eight four meters'."""
    text = number_word(whole)
    if fraction_digits:
        text += f" point {_digits_spoken(fraction_digits)}"
    unit = singular if (whole == 1 and not fraction_digits) else plural
    return f"{text} {unit}"


def distance_text(meters: float, precise: bool = True, unit: str = "auto") -> str:
    """precise: 1.843 -> 'one point eight four three meters' (mm accuracy),
    otherwise rounded to cm. unit: 'auto' (meters, below 1 m centimeters),
    or fixed 'm' / 'cm' / 'mm'."""
    if meters < 0:
        return "minus " + distance_text(-meters, precise, unit)
    mm_total = round(meters * 1000) if precise else round(meters * 100) * 10
    if unit == "mm":
        return _quantity(mm_total, "", "millimeter", "millimeters")
    if unit == "cm":
        cm, mm_digit = divmod(mm_total, 10)
        return _quantity(cm, str(mm_digit) if mm_digit else "", "centimeter", "centimeters")
    m, rest = divmod(mm_total, 1000)
    if unit == "auto" and m == 0:
        if rest == 0:
            return "zero"
        cm, mm_digit = divmod(rest, 10)
        return _quantity(cm, str(mm_digit) if mm_digit else "", "centimeter", "centimeters")
    digits = f"{rest:03d}".rstrip("0") if rest else ""
    return _quantity(m, digits, "meter", "meters")


def point_text(value: float, places: int, singular: str, plural: str) -> str:
    """2.128 -> 'two point one three square meters' (places=2);
    decimals are spoken digit by digit, trailing zeros are dropped."""
    if value < 0:
        return "minus " + point_text(-value, places, singular, plural)
    scaled = round(value * 10 ** places)
    whole, rest = divmod(scaled, 10 ** places)
    digits = f"{rest:0{places}d}".rstrip("0") if rest else ""
    return _quantity(whole, digits, singular, plural)


def area_text(value: float) -> str:
    return point_text(value, 2, "square meter", "square meters")


def volume_text(value: float) -> str:
    return point_text(value, 3, "cubic meter", "cubic meters")


def mode_speech(name: str) -> str:
    return f"{name} mode"


def error_speech() -> str:
    return "Measurement failed"


def partial_speech(index: int, distance: str) -> str:
    return f"{_ORDINALS[index]} length {distance}"


def area_result_speech(width: str, area: str) -> str:
    return f"Second length {width}, area {area}"


def volume_result_speech(length3: str, volume: str) -> str:
    return f"Third length {length3}, volume {volume}"


def result_speech(distance: str) -> str:
    return f"Result {distance}"


UI = {
    # cli
    "csv_path": "CSV: {path}",
    "csv_migrated": "Old CSV format detected — moved to {path}",
    "connected": "Connected to {mac} — press the measure button, I'm listening.",
    "connection_lost": "Connection lost — put the device back into Bluetooth "
                       "mode (Bluetooth button), retrying …",
    "connect_retry": "Connection attempt failed ({error}), retrying in 5 s",
    "exiting": "Exiting …",
    "mode_change": "Mode change: {name}",
    "unknown_mode": "unknown",
    "measure_error": "Measurement failed (mode {name})",
    "partial_line": "Partial measurement {index}: {value} m",
    "area_line": "Area: {area} m²  ({length} m × {width} m)",
    "volume_line": "Volume: {volume} m³  (3rd length {length} m)",
    "continuous_line": "Continuous: {value} m  (min {min}, max {max})",
    "calc_line": "{label}: {a} {sign} {b} = {result} {unit}",
    "label_add": "Addition",
    "label_subtract": "Subtraction",
    "label_area_add": "Area addition",
    "label_area_subtract": "Area subtraction",
    "unknown_frame": "Unknown frame type 0x{type}: {values}",
    "no_bluetooth": "Bluetooth Classic sockets are not available on this "
                    "system (socket.AF_BLUETOOTH is missing).",
    "no_mac": "No device address known. Pair the GLM via your system's "
              "Bluetooth settings and start with --mac XX:XX:XX:XX:XX:XX, "
              "or on Linux simply run \"glm-logger\" for automatic setup.",
    # speech / audio
    "tts_error": "[TTS error] {error}",
    "no_audio_player": "[TTS error] no audio player found ({players})",
    # config / voices
    "downloading_voice": "Downloading voice {name} (~60 MB) → {dir} …",
    "voice_ready": "Voice ready: {path}",
    # bluetooth setup
    "setup_intro": "No device configured — starting Bluetooth discovery. "
                   "Press the Bluetooth button on the GLM now …",
    "scanning": "Scanning for Bluetooth devices ({seconds} s) …",
    "found_device": "Found: {name} ({mac})",
    "no_device": "No GLM device found. Is the device switched on, the "
                 "Bluetooth button pressed, and no MeasureOn app connected? "
                 "Alternatively pair manually and start with --mac.",
    "multiple_devices": "Multiple GLM devices found — pick one with --mac:",
    "pairing": "Pairing with {name} ({mac}) …",
    "paired": "Paired and marked as trusted.",
    "pairing_failed": "Pairing failed ({error}) — please pair manually via "
                      "your Bluetooth settings and start with --mac.",
    "repairing": "Device is no longer paired — trying to pair again …",
    "config_saved": "Device saved to {path} — next time just run \"glm-logger\".",
    "manual_pairing": "Automatic pairing is Linux-only. Please pair the GLM "
                      "via your system's Bluetooth settings and start with "
                      "--mac XX:XX:XX:XX:XX:XX.",
}
