"""Command-line entry point: connect, announce, log."""

import argparse
import datetime
import socket
import sys
import time
from pathlib import Path

from glm50c import __version__, bt_setup, config, protocol, storage, style
from glm50c.lang import get_language
from glm50c.speech import Speaker
from glm50c.style import bold, faint


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

    def tilde(path) -> str:
        try:
            return "~/" + str(Path(path).relative_to(Path.home()))
        except ValueError:
            return str(path)

    print(bold(f"glm-logger {__version__}") + faint(" · Bosch GLM 50 C"))
    print(faint("  " + ui["banner_device"].format(mac=mac, channel=channel)))
    print(faint("  " + ui["banner_csv"].format(path=tilde(csv_path))))
    print(faint("  " + (ui["banner_voice"].format(voice=Path(speaker.voice_path).stem)
                        if speaker else ui["banner_mute"])), flush=True)
    if moved:
        print(style.warn(ui["csv_migrated"].format(path=tilde(moved))), flush=True)

    unit = args.unit or cfg.get("unit") or "auto"
    say = speaker.say if speaker else (lambda _t: None)
    dec = language.DECIMAL

    def fmt(value: float, places: int = 3) -> str:
        return f"{value:.{places}f}".replace(".", dec)

    def dist(meters: float) -> str:
        return language.distance_text(meters, precise=not args.coarse, unit=unit)

    reported_connected = False
    failures = 0
    try:
        while True:
            try:
                s = protocol.connect(mac, channel)
            except (TimeoutError, OSError):
                failures += 1
                if reported_connected:
                    print(style.warn("⚠ " + ui["connection_lost"]), flush=True)
                    reported_connected = False
                else:
                    print("\r" + faint("⟳ " + ui["waiting"].format(n=failures))
                          + style.clear_line(), end="", flush=True)
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
                print(ui["config_saved"].format(path=path), flush=True)

            print("\n" + style.good("✓ " + ui["connected"]), flush=True)
            say(language.connected_speech())
            reported_connected = True
            buffer = bytearray()
            partials: dict[int, float] = {}  # partial measurements (area/volume)
            watchdog = protocol.ConnectionWatchdog(time.monotonic())
            try:
                while True:
                    try:
                        data = s.recv(256)
                    except TimeoutError:
                        action = watchdog.tick(time.monotonic())
                        if action == "probe":
                            s.send(protocol.CMD_AUTOSYNC_ON)
                        elif action == "dead":
                            raise ConnectionResetError("stale connection")
                        continue
                    if not data:
                        raise ConnectionResetError("EOF")
                    watchdog.data_received(time.monotonic())
                    buffer += data
                    for kind, value in protocol.parse_frames(buffer):
                        now = datetime.datetime.now()
                        clock = now.strftime("%H:%M:%S")

                        def show(text, _kind=kind, _clock=clock):
                            print(style.event_line(_clock, _kind, text),
                                  flush=True)

                        if kind == "mode":
                            name = language.MODES.get(
                                value, f"{ui['unknown_mode']} ({value:g})")
                            show(ui["mode_change"].format(name=bold(name)))
                            say(language.mode_speech(
                                language.MODES.get(value, ui["unknown_mode"])))
                            partials.clear()
                        elif kind == "error":
                            name = language.MODES.get(value, f"{value:g}")
                            show(ui["measure_error"].format(name=name))
                            storage.append_row(csv_path, now, "error",
                                               distance="ERROR")
                            say(language.error_speech())
                        elif kind == "measurement":
                            show(bold(f"{fmt(value)} m") + "  "
                                 + faint(f"({fmt(value * 1000, 1)} mm)"))
                            storage.append_row(csv_path, now, "length",
                                               distance=storage.format_mm(value))
                            say(dist(value))
                        elif kind == "partial":
                            idx, w = value
                            partials[idx] = w
                            show(ui["partial_line"].format(
                                index=idx, value=bold(fmt(w))))
                            say(language.partial_speech(idx, dist(w)))
                        elif kind == "area":
                            f, length, width = value
                            show(ui["area_line"].format(
                                area=bold(fmt(f)), length=fmt(length),
                                width=fmt(width)))
                            storage.append_row(csv_path, now, "area",
                                               area=f"{f:.4f}",
                                               a=storage.format_mm(length),
                                               b=storage.format_mm(width))
                            say(language.area_result_speech(
                                dist(width), language.area_text(f)))
                            partials.clear()
                        elif kind == "volume":
                            v, l3 = value
                            show(ui["volume_line"].format(
                                volume=bold(fmt(v, 4)), length=fmt(l3)))
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
                            show(ui["continuous_line"].format(
                                value=bold(fmt(current)), min=fmt(mn),
                                max=fmt(mx)))
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
                            show(ui["calc_line"].format(
                                label=label, a=fmt(a), sign=sign,
                                b=fmt(b), result=bold(fmt(result)), unit="m"))
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
                            show(ui["calc_line"].format(
                                label=label, a=fmt(a), sign=sign,
                                b=fmt(b), result=bold(fmt(result)), unit="m²"))
                            storage.append_row(csv_path, now, kind,
                                               area=f"{result:.4f}",
                                               a=f"{a:.4f}", b=f"{b:.4f}")
                            say(language.result_speech(language.area_text(result)))
                        elif kind == "unknown":
                            ftype, floats = value
                            show(ui["unknown_frame"].format(
                                type=f"{ftype:02x}",
                                values=[round(x, 4) for x in floats]))
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
