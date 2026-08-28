"""User paths (platformdirs), TOML config, and Piper voice download."""

import sys
import tomllib
from pathlib import Path

import platformdirs

APP_NAME = "glm50c"


def data_dir() -> Path:
    return Path(platformdirs.user_data_dir(APP_NAME))


def voices_dir() -> Path:
    return data_dir() / "voices"


def default_csv_path() -> Path:
    return data_dir() / "measurements.csv"


def config_path() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME)) / "config.toml"


def load() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def save(cfg: dict) -> Path:
    """Write a flat key/value config (strings, ints, bools only)."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in sorted(cfg.items()):
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, int | float):
            lines.append(f"{key} = {value}")
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
    path.write_text("\n".join(lines) + "\n")
    return path


def ensure_voice(name: str, ui: dict) -> Path:
    """Return the local path of a Piper voice, downloading it if missing."""
    onnx = voices_dir() / f"{name}.onnx"
    if not onnx.exists():
        voices_dir().mkdir(parents=True, exist_ok=True)
        print(ui["downloading_voice"].format(name=name, dir=voices_dir()),
              file=sys.stderr, flush=True)
        from piper.download_voices import download_voice  # lazy import

        download_voice(name, voices_dir())
    return onnx
