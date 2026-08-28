"""Automatic Bluetooth setup on Linux (BlueZ): discover, pair, trust.

Drives `bluetoothctl` so the user never has to. Pairing runs in an
interactive pty session so PIN/passkey prompts can be answered
automatically (the GLM 50 C uses PIN 0000 if it asks at all).
"""

import os
import re
import subprocess
import sys
import time

DEFAULT_PIN = "0000"
SCAN_SECONDS = 12
_DEVICE_RE = re.compile(r"Device ((?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}) (.+)$")


def available() -> bool:
    return sys.platform.startswith("linux")


def _bluetoothctl(*args: str, timeout: float = 15) -> str:
    try:
        result = subprocess.run(["bluetoothctl", *args], capture_output=True,
                                text=True, timeout=timeout)
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def known_devices() -> list[tuple[str, str]]:
    devices = []
    for line in _bluetoothctl("devices").splitlines():
        m = _DEVICE_RE.search(line)
        if m:
            devices.append((m.group(1).upper(), m.group(2).strip()))
    return devices


def discover_glm(seconds: int = SCAN_SECONDS) -> list[tuple[str, str]]:
    """Scan for a while, then return known devices whose name contains GLM."""
    _bluetoothctl("--timeout", str(seconds), "scan", "on", timeout=seconds + 10)
    return [(mac, name) for mac, name in known_devices() if "GLM" in name.upper()]


def is_paired(mac: str) -> bool:
    return "Paired: yes" in _bluetoothctl("info", mac)


def pair_and_trust(mac: str, pin: str = DEFAULT_PIN,
                   timeout: float = 45) -> tuple[bool, str]:
    """Pair and trust via an interactive bluetoothctl session.

    Answers PIN and confirmation prompts automatically. Returns
    (ok, detail); detail carries the failure line on error."""
    import pty      # Unix-only modules — imported here so the package
    import select   # stays importable on Windows

    master, slave = pty.openpty()
    try:
        proc = subprocess.Popen(["bluetoothctl"], stdin=slave, stdout=slave,
                                stderr=slave, close_fds=True)
    except FileNotFoundError:
        os.close(master)
        os.close(slave)
        return False, "bluetoothctl not found"
    os.close(slave)

    def send(cmd: str):
        os.write(master, (cmd + "\n").encode())

    paired = False
    detail = ""
    output = ""
    answered_pin = False
    answered_confirm = False
    try:
        send("power on")
        send("default-agent")
        send(f"pair {mac}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.5)
            if not ready:
                continue
            try:
                chunk = os.read(master, 4096)
            except OSError:  # session ended
                break
            if not chunk:
                break
            output += chunk.decode(errors="replace")
            if not answered_pin and "Enter PIN code" in output:
                send(pin)
                answered_pin = True
            if not answered_confirm and ("Confirm passkey" in output
                                         or "(yes/no)" in output):
                send("yes")
                answered_confirm = True
            if "Pairing successful" in output or "AlreadyExists" in output:
                paired = True
                break
            failure = re.search(r"(Failed to pair.*|org\.bluez\.Error\.\S+"
                                r"|Device .* not available)", output)
            if failure:
                detail = failure.group(1).strip()
                break
        else:
            detail = "timeout"
        if paired:
            send(f"trust {mac}")
            time.sleep(1)
        send("quit")
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        os.close(master)
    if not paired and not detail:
        detail = "timeout"
    return paired, detail
