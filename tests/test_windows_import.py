"""The CLI must stay importable on Windows, where Unix-only stdlib modules
(pty, fcntl, termios, tty, grp, pwd) do not exist. Simulate their absence."""

import builtins
import importlib
import sys

UNIX_ONLY = {"pty", "fcntl", "termios", "tty", "grp", "pwd"}


def test_cli_imports_without_unix_only_modules(monkeypatch):
    for name in list(sys.modules):
        if name == "glm50c" or name.startswith("glm50c."):
            monkeypatch.delitem(sys.modules, name)
    for name in UNIX_ONLY:
        monkeypatch.delitem(sys.modules, name, raising=False)

    real_import = builtins.__import__

    def no_unix_import(name, *args, **kwargs):
        if name in UNIX_ONLY:
            raise ModuleNotFoundError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_unix_import)
    importlib.import_module("glm50c.cli")
