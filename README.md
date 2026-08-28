# glm50c

🇩🇪 [Deutsche Version](README.de.md)

Listen to your **Bosch GLM 50 C** laser distance meter: every press of the
measure button is received over Bluetooth, **read aloud** (Piper TTS, offline)
and **logged to CSV** — hands-free measuring while you're up a ladder.

Talks to the device directly over Bluetooth Classic RFCOMM using only the
Python standard library socket — no root, no `rfcomm bind`, no pybluez. The
protocol was reverse engineered; see [PROTOCOL.md](PROTOCOL.md).

Supported measuring modes: length, continuous, area, volume,
addition/subtraction (length and area), plus error frames.

## Requirements

- A Bosch GLM 50 C (model 0601072C00)
- Linux with BlueZ (Windows is experimental — see below; macOS is not
  supported, CPython lacks Bluetooth sockets there)
- Python ≥ 3.11
- An audio player for speech output (PipeWire `pw-play`, PulseAudio `paplay`
  or ALSA `aplay` — any modern desktop has one)

## Install

```console
pipx install git+https://github.com/CHANGEME/glm50c
```

(or `pip install git+…` into a venv of your choice)

## First run

Put the GLM into Bluetooth mode (press its Bluetooth button; make sure the
MeasureOn phone app is **not** connected), then:

```console
glm-logger
```

On the first run the tool takes care of everything:

1. scans for the device, pairs and trusts it automatically (Linux/BlueZ),
2. downloads the voice model for your language (~60 MB, once),
3. connects and saves the device address — from then on, plain `glm-logger`
   reconnects directly.

Press the measure button on the device; every result is spoken and logged.
`Ctrl-C` exits.

## Usage

```text
glm-logger [--mac MAC] [--channel N] [--csv FILE] [--lang {de,en}]
           [--voice NAME] [--voice-path FILE] [--mute] [--coarse]
           [--unit {auto,m,cm,mm}] [--setup]
```

| Flag | Meaning |
|---|---|
| `--lang de/en` | speech + console language (default: system locale) |
| `--mac` | device address (default: saved config / auto-setup) |
| `--channel` | RFCOMM channel (default: 5) |
| `--csv FILE` | log file (default: see *Files* below) |
| `--voice NAME` | Piper voice, e.g. `de_DE-kerstin-low` (auto-downloaded) |
| `--voice-path FILE` | use a local Piper model instead |
| `--mute` | no speech, log only |
| `--coarse` | announce rounded to centimeters |
| `--unit` | force announcement unit (default `auto`: meters, below 1 m centimeters) |
| `--setup` | run Bluetooth discovery/pairing again |

## Files

| What | Where (Linux) |
|---|---|
| Measurement log | `~/.local/share/glm50c/measurements.csv` |
| Voice models | `~/.local/share/glm50c/voices/` |
| Config | `~/.config/glm50c/config.toml` |

The config is written automatically after the first successful connection
(keys: `mac`, `channel`; you may also set `lang`, `voice`, `unit`, `csv`).
If you already have Piper `.onnx` + `.onnx.json` files, drop them into the
voices directory to skip the download.

### CSV format

Semicolon-separated, language-invariant English header:

```csv
timestamp;mode;distance_mm;area_m2;volume_m3;value_a;value_b
```

`distance_mm` holds the main value (or `ERROR`); `value_a`/`value_b` hold
extras depending on mode (continuous min/max, area length/width, volume
lengths 1/2, add/subtract operands — mm; area add/subtract operands — m²).
Files with an older header are moved aside automatically, never mixed.

## Windows (experimental)

CPython exposes Bluetooth RFCOMM sockets on Windows too, and speech output
uses the built-in `winsound`. Pair the GLM via Windows Bluetooth settings
first, then run `glm-logger --mac XX:XX:XX:XX:XX:XX`. This path is untested
on real hardware — reports welcome.

## Development

```console
uv sync --group dev
uv run pytest
uv run ruff check .
```

The protocol parser and the number verbalizers are pure functions and fully
unit-tested; everything touching the device is exercised by hand.

## License

[MIT](LICENSE)
