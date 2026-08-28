# Changelog

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
