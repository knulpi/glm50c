"""Deutsche Ansagen und Konsolen-Texte.

Der Zahl-zu-Wort-Generator stammt unverändert aus dem ursprünglichen Skript;
sein Verhalten ist durch tests/test_lang_de.py eingefroren.
"""

NAME = "de"
DEFAULT_VOICE = "de_DE-thorsten-medium"
DECIMAL = ","  # Dezimaltrennzeichen für die Konsolenanzeige

MODES = {1.0: "Länge", 2.0: "Dauermessung", 4.0: "Fläche", 7.0: "Volumen"}

EINER = ["null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
         "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn",
         "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
ZEHNER = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig",
          "siebzig", "achtzig", "neunzig"]

_ORDINALS = {1: "Erste", 2: "Zweite", 3: "Dritte"}


def zahlwort(n: int) -> str:
    """0..99999 als deutsches Zahlwort ('ein' statt 'eins', wie in 'ein Meter')."""
    if n >= 1000:
        t, r = divmod(n, 1000)
        rest = "eins" if r == 1 else (zahlwort(r) if r else "")
        return f"{zahlwort(t)}tausend{rest}"
    if n >= 100:
        h, r = divmod(n, 100)
        rest = "eins" if r == 1 else (zahlwort(r) if r else "")
        return f"{EINER[h]}hundert{rest}"
    if n < 20:
        return EINER[n]
    z, e = divmod(n, 10)
    if e == 0:
        return ZEHNER[z]
    return f"{EINER[e]}und{ZEHNER[z]}"


def _standalone(n: int, komma: str) -> str:
    """Zahlwort für alleinstehende Nennung: 'eins Komma …', aber 'ein <Einheit>'."""
    if n == 1:
        return "eins" if komma else "ein"
    return zahlwort(n)


def distance_text(meters: float, precise: bool = True, unit: str = "auto") -> str:
    """precise: 1.843 -> 'ein Meter vierundachtzig Komma drei' (mm-genau),
    sonst auf cm gerundet. unit: 'auto' (Meter, unter 1 m Zentimeter),
    oder fest 'm' / 'cm' / 'mm'."""
    if meters < 0:
        return "minus " + distance_text(-meters, precise, unit)
    mm_gesamt = round(meters * 1000) if precise else round(meters * 100) * 10
    if unit == "mm":
        return f"{_standalone(mm_gesamt, '')} Millimeter"
    if unit == "cm":
        cm, mm_ziffer = divmod(mm_gesamt, 10)
        komma = f" Komma {'eins' if mm_ziffer == 1 else EINER[mm_ziffer]}" if mm_ziffer else ""
        return f"{_standalone(cm, komma)}{komma} Zentimeter"
    m, rest = divmod(mm_gesamt, 1000)
    cm, mm_ziffer = divmod(rest, 10)
    komma = f" Komma {'eins' if mm_ziffer == 1 else EINER[mm_ziffer]}" if mm_ziffer else ""
    if unit == "auto" and m == 0:
        if rest == 0:
            return "null"
        return f"{_standalone(cm, komma)}{komma} Zentimeter"
    text = f"{zahlwort(m)} Meter"
    if cm:
        text += f" {'eins' if cm == 1 else zahlwort(cm)}"
    return text + komma


def komma_text(wert: float, stellen: int, einheit: str) -> str:
    """2.128 -> 'zwei Komma eins drei Quadratmeter' (stellen=2);
    Nachkommastellen werden als einzelne Ziffern gesprochen, End-Nullen entfallen."""
    if wert < 0:
        return "minus " + komma_text(-wert, stellen, einheit)
    skal = round(wert * 10 ** stellen)
    ganz, rest = divmod(skal, 10 ** stellen)
    komma = ""
    if rest:
        ziffern = f"{rest:0{stellen}d}".rstrip("0")
        gesprochen = " ".join("eins" if z == "1" else EINER[int(z)]
                              for z in ziffern)
        komma = f" Komma {gesprochen}"
    return f"{_standalone(ganz, komma)}{komma} {einheit}"


def area_text(value: float) -> str:
    return komma_text(value, 2, "Quadratmeter")


def volume_text(value: float) -> str:
    return komma_text(value, 3, "Kubikmeter")


def mode_speech(name: str) -> str:
    return f"Modus {name}"


def error_speech() -> str:
    return "Messfehler"


def partial_speech(index: int, distance: str) -> str:
    return f"{_ORDINALS[index]} Länge {distance}"


def area_result_speech(width: str, area: str) -> str:
    return f"Zweite Länge {width}, Fläche {area}"


def volume_result_speech(length3: str, volume: str) -> str:
    return f"Dritte Länge {length3}, Volumen {volume}"


def result_speech(distance: str) -> str:
    return f"Ergebnis {distance}"


def connected_speech() -> str:
    return "Verbunden"


UI = {
    # cli
    "banner_device": "Gerät   {mac} · Kanal {channel}",
    "banner_csv": "CSV     {path}",
    "banner_voice": "Stimme  {voice}",
    "banner_mute": "Ansage  aus",
    "csv_migrated": "Altes CSV-Format erkannt — verschoben nach {path}",
    "connected": "Verbunden — Messtaste am GLM drücken, ich höre zu.",
    "connection_lost": "Verbindung verloren — Bluetooth-Taste am Gerät "
                       "drücken, ich verbinde automatisch neu …",
    "waiting": "Warte auf das Gerät … Versuch {n} (Bluetooth-Taste am GLM drücken)",
    "exiting": "Beende …",
    "mode_change": "Moduswechsel: {name}",
    "unknown_mode": "unbekannt",
    "measure_error": "Messfehler (Modus {name})",
    "partial_line": "{index}. Teilmessung: {value} m",
    "area_line": "Fläche: {area} m²  ({length} m × {width} m)",
    "volume_line": "Volumen: {volume} m³  (3. Länge {length} m)",
    "continuous_line": "Dauermessung: {value} m  (min {min}, max {max})",
    "calc_line": "{label}: {a} {sign} {b} = {result} {unit}",
    "label_add": "Addition",
    "label_subtract": "Subtraktion",
    "label_area_add": "Flächen-Addition",
    "label_area_subtract": "Flächen-Subtraktion",
    "unknown_frame": "Unbekannter Frame-Typ 0x{type}: {values}",
    "no_bluetooth": "Bluetooth-Classic-Sockets sind auf diesem System nicht "
                    "verfügbar (socket.AF_BLUETOOTH fehlt).",
    "no_mac": "Keine Geräte-Adresse bekannt. Kopple das GLM über die "
              "System-Bluetooth-Einstellungen und starte mit "
              "--mac XX:XX:XX:XX:XX:XX, oder nutze unter Linux einfach "
              "»glm-logger« für die automatische Einrichtung.",
    # speech / audio
    "tts_error": "[TTS-Fehler] {error}",
    "no_audio_player": "[TTS-Fehler] kein Audio-Player gefunden ({players})",
    # config / voices
    "downloading_voice": "Lade Stimme {name} herunter (~60 MB) → {dir} …",
    "voice_ready": "Stimme bereit: {path}",
    # bluetooth setup
    "setup_intro": "Kein Gerät konfiguriert — starte Bluetooth-Suche. "
                   "Drücke jetzt die Bluetooth-Taste am GLM …",
    "scanning": "Suche nach Bluetooth-Geräten ({seconds} s) …",
    "found_device": "Gefunden: {name} ({mac})",
    "no_device": "Kein GLM-Gerät gefunden. Ist das Gerät eingeschaltet, die "
                 "Bluetooth-Taste gedrückt und keine MeasureOn-App verbunden? "
                 "Alternativ manuell koppeln und mit --mac starten.",
    "multiple_devices": "Mehrere GLM-Geräte gefunden — bitte eins mit --mac auswählen:",
    "pairing": "Kopple mit {name} ({mac}) …",
    "paired": "Gekoppelt und als vertrauenswürdig markiert.",
    "pairing_failed": "Kopplung fehlgeschlagen ({error}) — bitte manuell über die "
                      "Bluetooth-Einstellungen koppeln und mit --mac starten.",
    "repairing": "Gerät ist nicht mehr gekoppelt — versuche erneute Kopplung …",
    "config_saved": "Gerät gespeichert in {path} — nächstes Mal reicht »glm-logger«.",
    "manual_pairing": "Automatische Kopplung gibt es nur unter Linux. Bitte das "
                      "GLM über die System-Bluetooth-Einstellungen koppeln und "
                      "mit --mac XX:XX:XX:XX:XX:XX starten.",
}
