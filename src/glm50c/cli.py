"""Command-line entry point: connect, announce, log."""

import argparse
import datetime
import socket
import sys
import time
from pathlib import Path

from glm50c import __version__, bt_setup, config, protocol, storage
from glm50c.lang import get_language
from glm50c.speech import Speaker


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="glm-logger",
        description="Bosch GLM 50 C: announce and log measurements over Bluetooth")
    ap.add_argument("--mac",
                    help="Bluetooth address of the GLM (default: config / auto-setup)")
    ap.add_argument("--channel", type=int,
                    help=f"RFCOMM channel (default: {protocol.DEFAULT_CHANNEL})")
    ap.add_argument("--csv", type=Path,
                    help="CSV log file (default: user data directory)")
    ap.add_argument("--lang", choices=["de", "en"],
                    help="language for speech and console output "
                         "(default: system locale)")
    ap.add_argument("--voice",
                    help="Piper voice name, e.g. de_DE-thorsten-medium "
                         "(downloaded automatically)")
    ap.add_argument("--voice-path", type=Path,
                    help="path to a local Piper model (overrides --voice)")
    ap.add_argument("--mute", action="store_true", help="no TTS, log only")
    ap.add_argument("--coarse", action="store_true",
                    help="announce rounded to centimeters instead of mm-exact")
    ap.add_argument("--unit", choices=["auto", "m", "cm", "mm"],
                    help="always announce in this unit (default: auto = "
                         "meters, below 1 m centimeters)")
    ap.add_argument("--setup", action="store_true",
                    help="force Bluetooth discovery and pairing again")
    ap.add_argument("--version", action="version",
                    version=f"%(prog)s {__version__}")
    # Hidden German aliases (backward compatibility with the original script)
    ap.add_argument("--kanal", dest="channel", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--stumm", dest="mute", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--grob", dest="coarse", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--einheit", dest="unit", choices=["auto", "m", "cm", "mm"],
                    help=argparse.SUPPRESS)
    return ap


def run_setup(ui) -> str:
    """Discover, pair and trust the GLM automatically (Linux). Returns the MAC."""
    if not bt_setup.available():
        print(ui["manual_pairing"], file=sys.stderr)
        sys.exit(1)
    print(ui["setup_intro"], flush=True)
    print(ui["scanning"].format(seconds=bt_setup.SCAN_SECONDS), flush=True)
    found = bt_setup.discover_glm()
    if not found:
        print(ui["no_device"], file=sys.stderr)
        sys.exit(1)
    if len(found) > 1:
        print(ui["multiple_devices"])
        for mac, name in found:
            print(f"  {mac}  {name}")
        sys.exit(1)
    mac, name = found[0]
    print(ui["found_device"].format(name=name, mac=mac))
    if not bt_setup.is_paired(mac):
        print(ui["pairing"].format(name=name, mac=mac), flush=True)
        ok, detail = bt_setup.pair_and_trust(mac)
        if not ok:
            print(ui["pairing_failed"].format(error=detail), file=sys.stderr)
            sys.exit(1)
        print(ui["paired"])
    return mac


def main():
    args = build_parser().parse_args()
    cfg = config.load()
    language = get_language(args.lang or cfg.get("lang"))
    ui = language.UI

    if not hasattr(socket, "AF_BLUETOOTH"):
        print(ui["no_bluetooth"], file=sys.stderr)
        sys.exit(1)

    mac = args.mac or cfg.get("mac")
    channel = args.channel or cfg.get("channel") or protocol.DEFAULT_CHANNEL
    if args.setup or not mac:
        mac = run_setup(ui)
    mac = mac.upper()

    speaker = None
    if not args.mute:
        if args.voice_path:
            voice_path = args.voice_path
        else:
            voice_name = args.voice or cfg.get("voice") or language.DEFAULT_VOICE
            try:
                voice_path = config.ensure_voice(voice_name, ui)
            except Exception as e:  # e.g. no network: keep logging, just mute
                print(ui["tts_error"].format(error=e), file=sys.stderr)
                voice_path = None
        if voice_path:
            speaker = Speaker(voice_path, ui)
            speaker.start()

    csv_path = args.csv or (Path(cfg["csv"]) if cfg.get("csv")
                            else config.default_csv_path())
    moved = storage.migrate_old_csv(csv_path)
    if moved:
        print(ui["csv_migrated"].format(path=moved))
    print(ui["csv_path"].format(path=csv_path))

    unit = args.unit or cfg.get("unit") or "auto"
    say = speaker.say if speaker else (lambda _t: None)

    def dist(meters: float) -> str:
        return language.distance_text(meters, precise=not args.coarse, unit=unit)

    reported_connected = False
    failures = 0
    try:
        while True:
            try:
                s = protocol.connect(mac, channel)
            except (TimeoutError, OSError) as e:
                failures += 1
                if reported_connected:
                    print(ui["connection_lost"])
                    reported_connected = False
                else:
                    print(ui["connect_retry"].format(error=e), end="\r")
                # Heal a lost pairing (e.g. device was re-paired with a phone)
                if failures == 3 and bt_setup.available() and not bt_setup.is_paired(mac):
                    print("\n" + ui["repairing"], flush=True)
                    ok, detail = bt_setup.pair_and_trust(mac)
                    print(ui["paired"] if ok
                          else ui["pairing_failed"].format(error=detail))
                time.sleep(5)
                continue
            failures = 0

            if cfg.get("mac") != mac or cfg.get("channel") != channel:
                cfg["mac"], cfg["channel"] = mac, channel
                path = config.save(cfg)
                print(ui["config_saved"].format(path=path))

            print("\n" + ui["connected"].format(mac=mac), flush=True)
            reported_connected = True
            buffer = bytearray()
            partials: dict[int, float] = {}  # partial measurements (area/volume)
            try:
                while True:
                    try:
                        data = s.recv(256)
                    except TimeoutError:
                        continue
                    if not data:
                        raise ConnectionResetError("EOF")
                    buffer += data
                    for kind, value in protocol.parse_frames(buffer):
                        now = datetime.datetime.now()
                        ts = now.isoformat(timespec="seconds")

                        if kind == "mode":
                            name = language.MODES.get(
                                value, f"{ui['unknown_mode']} ({value:g})")
                            print(f"{ts}  " + ui["mode_change"].format(name=name),
                                  flush=True)
                            say(language.mode_speech(
                                language.MODES.get(value, ui["unknown_mode"])))
                            partials.clear()
                        elif kind == "error":
                            name = language.MODES.get(value, f"{value:g}")
                            print(f"{ts}  " + ui["measure_error"].format(name=name),
                                  flush=True)
                            storage.append_row(csv_path, now, "error",
                                               distance="ERROR")
                            say(language.error_speech())
                        elif kind == "measurement":
                            print(f"{ts}  {value:.3f} m  ({value * 1000:.1f} mm)",
                                  flush=True)
                            storage.append_row(csv_path, now, "length",
                                               distance=storage.format_mm(value))
                            say(dist(value))
                        elif kind == "partial":
                            idx, w = value
                            partials[idx] = w
                            print(f"{ts}  " + ui["partial_line"].format(
                                index=idx, value=f"{w:.3f}"), flush=True)
                            say(language.partial_speech(idx, dist(w)))
                        elif kind == "area":
                            f, length, width = value
                            print(f"{ts}  " + ui["area_line"].format(
                                area=f"{f:.3f}", length=f"{length:.3f}",
                                width=f"{width:.3f}"), flush=True)
                            storage.append_row(csv_path, now, "area",
                                               area=f"{f:.4f}",
                                               a=storage.format_mm(length),
                                               b=storage.format_mm(width))
                            say(language.area_result_speech(
                                dist(width), language.area_text(f)))
                            partials.clear()
                        elif kind == "volume":
                            v, l3 = value
                            print(f"{ts}  " + ui["volume_line"].format(
                                volume=f"{v:.4f}", length=f"{l3:.3f}"), flush=True)
                            storage.append_row(csv_path, now, "volume",
                                               distance=storage.format_mm(l3),
                                               volume=f"{v:.4f}",
                                               a=storage.format_mm(partials.get(1)),
                                               b=storage.format_mm(partials.get(2)))
                            say(language.volume_result_speech(
                                dist(l3), language.volume_text(v)))
                            partials.clear()
                        elif kind == "continuous":
                            current, mn, mx = value
                            print(f"{ts}  " + ui["continuous_line"].format(
                                value=f"{current:.3f}", min=f"{mn:.3f}",
                                max=f"{mx:.3f}"), flush=True)
                            storage.append_row(csv_path, now, "continuous",
                                               distance=storage.format_mm(current),
                                               a=storage.format_mm(mn),
                                               b=storage.format_mm(mx))
                            say(dist(current))
                        elif kind in ("add", "subtract"):
                            result, a, b = value
                            sign = "+" if kind == "add" else "−"
                            label = ui["label_add" if kind == "add"
                                       else "label_subtract"]
                            print(f"{ts}  " + ui["calc_line"].format(
                                label=label, a=f"{a:.3f}", sign=sign,
                                b=f"{b:.3f}", result=f"{result:.3f}", unit="m"),
                                flush=True)
                            storage.append_row(csv_path, now, kind,
                                               distance=storage.format_mm(result),
                                               a=storage.format_mm(a),
                                               b=storage.format_mm(b))
                            say(language.result_speech(dist(result)))
                        elif kind in ("area_add", "area_subtract"):
                            result, a, b = value
                            sign = "+" if kind == "area_add" else "−"
                            label = ui["label_area_add" if kind == "area_add"
                                       else "label_area_subtract"]
                            print(f"{ts}  " + ui["calc_line"].format(
                                label=label, a=f"{a:.3f}", sign=sign,
                                b=f"{b:.3f}", result=f"{result:.3f}", unit="m²"),
                                flush=True)
                            storage.append_row(csv_path, now, kind,
                                               area=f"{result:.4f}",
                                               a=f"{a:.4f}", b=f"{b:.4f}")
                            say(language.result_speech(language.area_text(result)))
                        elif kind == "unknown":
                            ftype, floats = value
                            print(f"{ts}  " + ui["unknown_frame"].format(
                                type=f"{ftype:02x}",
                                values=[round(x, 4) for x in floats]), flush=True)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                try:
                    s.close()
                except OSError:
                    pass
                # back into the reconnect loop
    except KeyboardInterrupt:
        print("\n" + ui["exiting"])
        if speaker:
            speaker.shutdown()


if __name__ == "__main__":
    main()
