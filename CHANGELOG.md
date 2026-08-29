# Changelog

## 0.3.1 — 2026-08-29

- Release binaries now carry the version in their file name
  (e.g. `glm-logger-v0.3.1-linux-x86_64`).

## 0.3.0 — 2026-08-29

- Speak a short confirmation ("Connected" / "Verbunden") whenever the
  device connects or reconnects, so you know hands-free that measuring
  is ready again.

## 0.2.1 — 2026-08-29

- Fix the released Linux binary reporting "Bluetooth Classic sockets are
  not available": the release build now uses a system Python (uv's managed
  Pythons are compiled without `socket.AF_BLUETOOTH`), and the workflow
  fails early if the build interpreter lacks Bluetooth support.

## 0.2.0 — 2026-08-29

- Standalone executables for Linux and Windows on the GitHub releases
  page (PyInstaller one-file builds, no Python required).
- Prettier console output: colored event glyphs (●▰▣◐Σ✗), bold primary
  values, dim timestamps and details, a startup banner and a single
  self-updating "waiting for device" status line. Pure ANSI — no new
  dependencies; colors switch off automatically for pipes and `NO_COLOR`,
  and are enabled on modern Windows terminals via VT mode.
- Console numbers use the language's decimal separator (German: comma).
- One CSV file per run: the default log is now
  `measurements-<start time>.csv`, created on the first measurement.
  An explicit `--csv` path or a `csv` entry in the config still names
  one fixed file.

## 0.1.0 — 2026-08-28

First packaged release.

- Restructured the original single-file script into the `glm50c` package
  with a `glm-logger` entry point (`pipx install` ready).
- German **and** English speech + console output (`--lang`, autodetected
  from the system locale).
- Piper voice models are downloaded automatically on first use into the
  user data directory (no more vendored `.onnx` files).
- Automatic Bluetooth setup on Linux: discovery, pairing, trust — the
  device address is saved to a config file after the first connection.
- Measurement CSV moved to the user's documents folder
  (`~/Documents/glm50c/`); language-invariant English header. Old-format
  files are moved aside automatically.
- Experimental Windows support (RFCOMM socket + `winsound` playback).
- Unit tests for the frame parser, both number verbalizers and CSV storage.

Breaking changes vs. the original script: `--stimme thorsten/kerstin` was
replaced by `--voice <full piper name>`; the CSV header and mode values are
English now. The German flags `--kanal`, `--stumm`, `--grob`, `--einheit`
still work as hidden aliases.
