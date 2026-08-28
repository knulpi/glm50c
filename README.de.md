# glm50c

🇬🇧 [English version](README.md)

Der **Bosch GLM 50 C** Laser-Entfernungsmesser, zum Zuhören: Jeder Druck auf
die Messtaste wird per Bluetooth empfangen, **laut vorgelesen** (Piper-TTS,
offline) und **in eine CSV geloggt** — freihändig messen, auch oben auf der
Leiter.

Die Verbindung läuft direkt über Bluetooth Classic RFCOMM mit dem
Stdlib-Socket von Python — kein root, kein `rfcomm bind`, kein pybluez. Das
Protokoll ist reverse-engineert; siehe [PROTOCOL.md](PROTOCOL.md).

Unterstützte Messmodi: Länge, Dauermessung, Fläche, Volumen,
Addition/Subtraktion (Länge und Fläche), dazu Fehlmessungs-Frames.

## Voraussetzungen

- Ein Bosch GLM 50 C (Modell 0601072C00)
- Linux mit BlueZ (Windows experimentell — siehe unten; macOS geht nicht,
  CPython hat dort keine Bluetooth-Sockets)
- Python ≥ 3.11
- Ein Audio-Player für die Sprachausgabe (PipeWire `pw-play`, PulseAudio
  `paplay` oder ALSA `aplay` — jeder moderne Desktop hat einen davon)

## Installation

```console
pipx install git+https://github.com/knulpi/glm50c
```

(oder `pip install git+…` in ein venv deiner Wahl)

## Erster Start

Das GLM in den Bluetooth-Modus bringen (Bluetooth-Taste drücken; die
MeasureOn-Handy-App darf **nicht** verbunden sein), dann:

```console
glm-logger
```

Beim ersten Start kümmert sich das Tool um alles:

1. sucht das Gerät, koppelt es automatisch und markiert es als
   vertrauenswürdig (Linux/BlueZ),
2. lädt das Sprachmodell für deine Sprache herunter (~60 MB, einmalig),
3. verbindet sich und speichert die Geräteadresse — danach reicht immer ein
   schlichtes `glm-logger`.

Messtaste am Gerät drücken; jedes Ergebnis wird angesagt und geloggt.
`Strg-C` beendet.

## Benutzung

```text
glm-logger [--mac MAC] [--channel N] [--csv DATEI] [--lang {de,en}]
           [--voice NAME] [--voice-path DATEI] [--mute] [--coarse]
           [--unit {auto,m,cm,mm}] [--setup]
```

| Flag | Bedeutung |
|---|---|
| `--lang de/en` | Sprache für Ansagen + Konsole (Standard: System-Locale) |
| `--mac` | Geräteadresse (Standard: gespeicherte Config / Auto-Setup) |
| `--channel` | RFCOMM-Kanal (Standard: 5) |
| `--csv DATEI` | Logdatei (Standard: siehe *Dateien*) |
| `--voice NAME` | Piper-Stimme, z. B. `de_DE-kerstin-low` (wird automatisch geladen) |
| `--voice-path DATEI` | lokales Piper-Modell verwenden |
| `--mute` | keine Ansagen, nur loggen |
| `--coarse` | Ansage auf Zentimeter gerundet |
| `--unit` | feste Ansage-Einheit (Standard `auto`: Meter, unter 1 m Zentimeter) |
| `--setup` | Bluetooth-Suche/Kopplung erneut ausführen |

Die deutschen Flags des ursprünglichen Skripts (`--kanal`, `--stumm`,
`--grob`, `--einheit`) funktionieren weiterhin.

## Dateien

| Was | Wo (Linux) |
|---|---|
| Messwerte-Log | `~/Dokumente/glm50c/measurements.csv` (dein XDG-Dokumente-Ordner) |
| Sprachmodelle | `~/.local/share/glm50c/voices/` |
| Config | `~/.config/glm50c/config.toml` |

Die Config wird nach der ersten erfolgreichen Verbindung automatisch
geschrieben (Keys: `mac`, `channel`; zusätzlich möglich: `lang`, `voice`,
`unit`, `csv`). Vorhandene Piper-Dateien (`.onnx` + `.onnx.json`) können in
das Stimmen-Verzeichnis kopiert werden, um den Download zu sparen.

### CSV-Format

Semikolon-getrennt, sprachunabhängiger englischer Kopf:

```csv
timestamp;mode;distance_mm;area_m2;volume_m3;value_a;value_b
```

`distance_mm` enthält den Hauptwert (oder `ERROR`); `value_a`/`value_b` sind
Zusatzwerte je nach Modus (Dauermessung min/max, Fläche Länge/Breite, Volumen
Länge 1/2, Add/Sub-Operanden — mm; Flächen-Add/Sub-Operanden — m²). Dateien
mit altem Kopf werden automatisch beiseitegelegt, nie gemischt.

## Windows (experimentell)

CPython bietet Bluetooth-RFCOMM-Sockets auch unter Windows, die Sprachausgabe
nutzt das eingebaute `winsound`. Das GLM zuerst über die
Windows-Bluetooth-Einstellungen koppeln, dann
`glm-logger --mac XX:XX:XX:XX:XX:XX`. Dieser Pfad ist auf echter Hardware
ungetestet — Rückmeldungen willkommen.

## Entwicklung

```console
uv sync --group dev
uv run pytest
uv run ruff check .
```

Frame-Parser und Zahl-Verbalisierer sind pure Funktionen mit vollständigen
Unit-Tests; alles mit Gerätekontakt wird von Hand getestet.

## Credits

Dieses Projekt ist in Co-Autorschaft mit **Claude (Fable 5)**, dem
KI-Modell von Anthropic, entstanden: der Umbau zum Paket, die englische
Sprachunterstützung und die Dokumentation stammen aus
Pair-Programming-Sessions damit. Das Protokoll-Reverse-Engineering wurde
an echter Hardware verifiziert.

## Lizenz

[MIT](LICENSE)
