#!/usr/bin/env python3
"""Bosch GLM 50 C (0601072C00): Messwerte über Bluetooth Classic SPP empfangen,
per Piper-TTS deutsch vorlesen und mit Zeitstempel in eine CSV loggen.

Verbindung: RFCOMM über Pythons Stdlib-Socket (AF_BLUETOOTH) — kein rfcomm bind,
kein root, kein pybluez. Das Gerät muss im Bluetooth-Modus sein und darf nicht
mit dem Handy (MeasureOn) verbunden sein.

Protokoll (empirisch verifiziert am 2026-08-28, BlueZ 5.85):
  TX  c0 55 02 01 00 1a          Auto-Sync einschalten -> Gerät pusht ab jetzt
                                 bei jedem Druck auf die Messtaste von selbst.
  RX  c0 55 10 <16 B Payload> <CRC>   20-Byte-Push-Frame.
      Frame-Typ (Byte 3): 0x02 Laser-Event; 0x06 Einzelmessung, Distanz =
      Float32 LE in Metern ab Byte 7; 0xF2 Moduswechsel (Float = Modus-ID:
      1 Länge, 2 Dauermessung, 4 Fläche); 0xFE Fehlmessung (Float = aktiver
      Modus, die Ursache — zu nah/zu weit — wird nicht unterschieden);
      0x12 Flächen-Ergebnis [m², Länge, Breite]; 0x0E/0x16/0x1A Teil-
      messungen [0, Länge, 0] (Fläche 1. bzw. Volumen 1./2.); 0x1E Volumen-
      Ergebnis [m³, 3. Länge, 0]; 0x0A Dauermessung [aktuell, min, max];
      0x42/0x46 Addition/Subtraktion [Ergebnis, a, b] in m; 0x4A/0x4E
      Flächen-Addition/-Subtraktion in m². Modus-IDs (0xF2): 1 Länge,
      2 Dauermessung, 4 Fläche, 7 Volumen; für Mess-Frames gilt:
      Modus-ID = (Typ - 2) / 4.
      Der CRC folgt keinem einfachen CRC-8-Schema (Brute-Force über
      Poly/Init/XorOut erfolglos); Validierung daher über Header + Länge.
"""

import argparse
import csv
import datetime
import io
import queue
import socket
import struct
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

MAC_DEFAULT = "XX:XX:XX:XX:XX:XX"
CHANNEL_DEFAULT = 5
FRAME_HEADER = b"\xc0\x55\x10"
FRAME_LEN = 20
CMD_AUTOSYNC_ON = bytes.fromhex("c0550201001a")
MODI = {1.0: "Länge", 2.0: "Dauermessung", 4.0: "Fläche", 7.0: "Volumen"}

BASE = Path(__file__).resolve().parent
STIMMEN = {
    "thorsten": BASE / "voices" / "de_DE-thorsten-medium.onnx",  # männlich
    "kerstin": BASE / "voices" / "de_DE-kerstin-low.onnx",       # weiblich
}
CSV_DEFAULT = BASE / "messungen.csv"

EINER = ["null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
         "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn",
         "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
ZEHNER = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig",
          "siebzig", "achtzig", "neunzig"]


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


def sprech_text(meter: float, praezise: bool = True, einheit: str = "auto") -> str:
    """praezise: 1.843 -> 'ein Meter vierundachtzig Komma drei' (mm-genau),
    sonst auf cm gerundet. einheit: 'auto' (Meter, unter 1 m Zentimeter),
    oder fest 'm' / 'cm' / 'mm'."""
    mm_gesamt = round(meter * 1000) if praezise else round(meter * 100) * 10
    if einheit == "mm":
        return f"{_standalone(mm_gesamt, '')} Millimeter"
    if einheit == "cm":
        cm, mm_ziffer = divmod(mm_gesamt, 10)
        komma = f" Komma {'eins' if mm_ziffer == 1 else EINER[mm_ziffer]}" if mm_ziffer else ""
        return f"{_standalone(cm, komma)}{komma} Zentimeter"
    m, rest = divmod(mm_gesamt, 1000)
    cm, mm_ziffer = divmod(rest, 10)
    komma = f" Komma {'eins' if mm_ziffer == 1 else EINER[mm_ziffer]}" if mm_ziffer else ""
    if einheit == "auto" and m == 0:
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


def qm_text(f: float) -> str:
    return komma_text(f, 2, "Quadratmeter")


def m3_text(v: float) -> str:
    return komma_text(v, 3, "Kubikmeter")


class Vorleser(threading.Thread):
    """TTS-Worker: lädt die Piper-Stimme einmal, spricht Texte aus einer Queue."""

    def __init__(self, voice_path: Path):
        super().__init__(daemon=True)
        self.queue: "queue.Queue[str|None]" = queue.Queue()
        self.voice_path = voice_path
        self.voice = None

    def run(self):
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(self.voice_path))
        while True:
            text = self.queue.get()
            if text is None:
                return
            try:
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    self.voice.synthesize_wav(text, wf)
                buf.seek(0)
                self._abspielen(buf.read())
            except Exception as e:
                print(f"[TTS-Fehler] {e}", file=sys.stderr)

    @staticmethod
    def _abspielen(wav_bytes: bytes):
        for player in (["pw-play", "-"], ["paplay"], ["aplay", "-q"]):
            try:
                subprocess.run(player, input=wav_bytes, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        print("[TTS-Fehler] kein Audio-Player (pw-play/paplay/aplay)", file=sys.stderr)

    def sag(self, text: str):
        self.queue.put(text)


CSV_KOPF = ["zeitstempel", "modus", "distanz_mm", "flaeche_m2", "volumen_m3",
            "wert_a", "wert_b"]
# distanz_mm = Hauptwert (Länge, aktueller Wert, Summe/Ergebnis, 3. Volumen-
# Länge) bzw. FEHLER. wert_a/b = Zusatzwerte, Einheit je nach Modus: mm bei
# Längenmodi (Dauermessung min/max, Fläche Länge/Breite, Volumen Länge 1/2,
# Addition/Subtraktion Operanden), m² bei Flächen-Addition/-Subtraktion.


def _mm(wert: float | None) -> str:
    # Gerät liefert mm-Auflösung; eine Nachkommastelle deckt 0,5-mm-Werte ab
    return "" if wert is None else f"{wert * 1000.0:.1f}".rstrip("0").rstrip(".")


def csv_anhaengen(pfad: Path, zeitpunkt: datetime.datetime, modus: str,
                  distanz: str = "", flaeche: str = "", volumen: str = "",
                  a: str = "", b: str = ""):
    neu = not pfad.exists()
    with open(pfad, "a", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if neu:
            w.writerow(CSV_KOPF)
        w.writerow([zeitpunkt.isoformat(timespec="seconds"), modus,
                    distanz, flaeche, volumen, a, b])


def csv_migrieren(pfad: Path):
    """Alte CSV (anderer Spaltenkopf) beiseitelegen statt gemischt weiterschreiben."""
    if not pfad.exists():
        return
    with open(pfad, newline="") as f:
        kopf = f.readline().strip()
    if kopf != ";".join(CSV_KOPF):
        alt = pfad.with_name(f"{pfad.stem}-alt-"
                             f"{datetime.datetime.now():%Y%m%d-%H%M%S}{pfad.suffix}")
        pfad.rename(alt)
        print(f"Altes CSV-Format erkannt — verschoben nach {alt}")


def verbinden(mac: str, kanal: int) -> socket.socket:
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    s.settimeout(10)
    s.connect((mac, kanal))
    s.send(CMD_AUTOSYNC_ON)
    s.settimeout(1)
    return s


def frames_verarbeiten(puffer: bytearray):
    """Vollständige Push-Frames aus dem Puffer schneiden, Distanzen liefern."""
    while True:
        idx = puffer.find(FRAME_HEADER)
        if idx < 0:
            # Auch Reste (z. B. Auto-Sync-Ack ohne c0-Präfix) irgendwann verwerfen
            if len(puffer) > 4 * FRAME_LEN:
                del puffer[:-len(FRAME_HEADER)]
            return
        if idx:
            del puffer[:idx]
        if len(puffer) < FRAME_LEN:
            return
        frame = bytes(puffer[:FRAME_LEN])
        del puffer[:FRAME_LEN]
        if frame[3] == 0x06:  # Einzelmessung (0x02 = Laser-Event, wird ignoriert)
            (meter,) = struct.unpack_from("<f", frame, 7)
            if 0.0 < meter < 100.0:
                yield ("ok", meter)
        elif frame[3] == 0xF2:  # Moduswechsel, Float = Modus-ID
            (code,) = struct.unpack_from("<f", frame, 7)
            yield ("modus", code)
        elif frame[3] == 0xFE:  # Fehlmessung; Float = aktiver Modus, NICHT die
            (code,) = struct.unpack_from("<f", frame, 7)  # Fehlerursache
            yield ("fehler", code)
        elif frame[3] == 0x12:  # Flächen-Ergebnis: [Fläche m², Länge, Breite]
            yield ("flaeche", struct.unpack_from("<fff", frame, 7))
        elif frame[3] in (0x0E, 0x16):  # 1. Teilmessung (Fläche bzw. Volumen)
            yield ("teil", (1, struct.unpack_from("<f", frame, 11)[0]))
        elif frame[3] == 0x1A:  # Volumen, 2. Teilmessung: [0, Länge, 0]
            yield ("teil", (2, struct.unpack_from("<f", frame, 11)[0]))
        elif frame[3] == 0x1E:  # Volumen-Ergebnis: [Volumen m³, 3. Länge, 0]
            yield ("volumen", struct.unpack_from("<ff", frame, 7))
        elif frame[3] == 0x0A:  # Dauermessung: [aktuell, min, max]
            yield ("dauer", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x42:  # Addition: [Summe, a, b]
            yield ("addition", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x46:  # Subtraktion: [Ergebnis, a, b]
            yield ("subtraktion", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x4A:  # Flächen-Addition: [Summe, a, b] in m²
            yield ("flaechen_addition", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x4E:  # Flächen-Subtraktion (nach Typmuster, unverifiziert)
            yield ("flaechen_subtraktion", struct.unpack_from("<fff", frame, 7))
        elif frame[3] != 0x02:  # Laser-Events ignorieren, Unbekanntes zeigen
            yield ("unbekannt", (frame[3], struct.unpack_from("<fff", frame, 7)))


def main():
    ap = argparse.ArgumentParser(description="GLM 50 C: Messwerte vorlesen + CSV-Log")
    ap.add_argument("--mac", default=MAC_DEFAULT)
    ap.add_argument("--kanal", type=int, default=CHANNEL_DEFAULT)
    ap.add_argument("--csv", type=Path, default=CSV_DEFAULT)
    ap.add_argument("--stimme", choices=sorted(STIMMEN), default="thorsten",
                    help="Sprecherstimme (kerstin = weiblich)")
    ap.add_argument("--voice", type=Path, default=None,
                    help="Pfad zu einem beliebigen Piper-Modell (überstimmt --stimme)")
    ap.add_argument("--stumm", action="store_true", help="kein TTS, nur loggen")
    ap.add_argument("--grob", action="store_true",
                    help="Ansage nur auf Zentimeter gerundet statt mm-genau")
    ap.add_argument("--einheit", choices=["auto", "m", "cm", "mm"], default="auto",
                    help="Ansage immer in dieser Maßeinheit (Standard: auto = "
                         "Meter, unter 1 m Zentimeter)")
    args = ap.parse_args()

    vorleser = None
    if not args.stumm:
        vorleser = Vorleser(args.voice or STIMMEN[args.stimme])
        vorleser.start()

    csv_migrieren(args.csv)
    print(f"CSV: {args.csv}")
    verbunden_gemeldet = False
    try:
        while True:
            try:
                s = verbinden(args.mac, args.kanal)
            except (OSError, socket.timeout) as e:
                if verbunden_gemeldet:
                    print("Verbindung verloren — Gerät wieder in den BT-Modus "
                          "bringen (Bluetooth-Taste), ich versuche es weiter …")
                    verbunden_gemeldet = False
                else:
                    print(f"Verbindungsversuch fehlgeschlagen ({e}), neuer Versuch in 5 s", end="\r")
                time.sleep(5)
                continue

            print(f"\nVerbunden mit {args.mac} — Messtaste drücken, ich höre zu.",
                  flush=True)
            verbunden_gemeldet = True
            puffer = bytearray()
            teil: dict[int, float] = {}  # Teilmessungen (Fläche/Volumen)
            try:
                while True:
                    try:
                        daten = s.recv(256)
                    except socket.timeout:
                        continue
                    if not daten:
                        raise ConnectionResetError("EOF")
                    puffer += daten
                    for art, wert in frames_verarbeiten(puffer):
                        jetzt = datetime.datetime.now()
                        ts = jetzt.isoformat(timespec="seconds")
                        sag = vorleser.sag if vorleser else (lambda _t: None)

                        def strecke(meter):
                            vorzeichen = "minus " if meter < 0 else ""
                            return vorzeichen + sprech_text(
                                abs(meter), praezise=not args.grob,
                                einheit=args.einheit)

                        ordinal = {1: "Erste", 2: "Zweite", 3: "Dritte"}

                        if art == "modus":
                            name = MODI.get(wert, f"unbekannt ({wert:g})")
                            print(f"{ts}  Moduswechsel: {name}", flush=True)
                            sag("Modus " + MODI.get(wert, "unbekannt"))
                            teil.clear()
                        elif art == "fehler":
                            name = MODI.get(wert, f"{wert:g}")
                            print(f"{ts}  Messfehler (Modus {name})", flush=True)
                            csv_anhaengen(args.csv, jetzt, "fehler",
                                          distanz="FEHLER")
                            sag("Messfehler")
                        elif art == "ok":
                            print(f"{ts}  {wert:.3f} m  ({wert * 1000:.1f} mm)",
                                  flush=True)
                            csv_anhaengen(args.csv, jetzt, "laenge",
                                          distanz=_mm(wert))
                            sag(strecke(wert))
                        elif art == "teil":
                            idx, w = wert
                            teil[idx] = w
                            print(f"{ts}  {idx}. Teilmessung: {w:.3f} m",
                                  flush=True)
                            sag(f"{ordinal[idx]} Länge " + strecke(w))
                        elif art == "flaeche":
                            f, l, b = wert
                            print(f"{ts}  Fläche: {f:.3f} m²  "
                                  f"({l:.3f} m × {b:.3f} m)", flush=True)
                            csv_anhaengen(args.csv, jetzt, "flaeche",
                                          flaeche=f"{f:.4f}",
                                          a=_mm(l), b=_mm(b))
                            sag("Zweite Länge " + strecke(b)
                                + ", Fläche " + qm_text(f))
                            teil.clear()
                        elif art == "volumen":
                            v, l3 = wert
                            print(f"{ts}  Volumen: {v:.4f} m³  "
                                  f"(3. Länge {l3:.3f} m)", flush=True)
                            csv_anhaengen(args.csv, jetzt, "volumen",
                                          distanz=_mm(l3), volumen=f"{v:.4f}",
                                          a=_mm(teil.get(1)), b=_mm(teil.get(2)))
                            sag("Dritte Länge " + strecke(l3)
                                + ", Volumen " + m3_text(v))
                            teil.clear()
                        elif art == "dauer":
                            akt, mn, mx = wert
                            print(f"{ts}  Dauermessung: {akt:.3f} m  "
                                  f"(min {mn:.3f}, max {mx:.3f})", flush=True)
                            csv_anhaengen(args.csv, jetzt, "dauer",
                                          distanz=_mm(akt),
                                          a=_mm(mn), b=_mm(mx))
                            sag(strecke(akt))
                        elif art in ("addition", "subtraktion"):
                            erg, a, b = wert
                            zeichen = "+" if art == "addition" else "−"
                            print(f"{ts}  {art.capitalize()}: {a:.3f} {zeichen} "
                                  f"{b:.3f} = {erg:.3f} m", flush=True)
                            csv_anhaengen(args.csv, jetzt, art,
                                          distanz=_mm(erg), a=_mm(a), b=_mm(b))
                            sag("Ergebnis " + strecke(erg))
                        elif art in ("flaechen_addition", "flaechen_subtraktion"):
                            erg, a, b = wert
                            zeichen = "+" if art == "flaechen_addition" else "−"
                            print(f"{ts}  {art.replace('_', '-').capitalize()}: "
                                  f"{a:.3f} {zeichen} {b:.3f} = {erg:.3f} m²",
                                  flush=True)
                            csv_anhaengen(args.csv, jetzt, art,
                                          flaeche=f"{erg:.4f}",
                                          a=f"{a:.4f}", b=f"{b:.4f}")
                            sag("Ergebnis " + qm_text(erg))
                        elif art == "unbekannt":
                            typ, floats = wert
                            print(f"{ts}  Unbekannter Frame-Typ 0x{typ:02x}: "
                                  f"{[round(x, 4) for x in floats]}", flush=True)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                try:
                    s.close()
                except OSError:
                    pass
                # zurück in die Reconnect-Schleife
    except KeyboardInterrupt:
        print("\nBeende …")
        if vorleser:
            vorleser.queue.put(None)
            vorleser.join(timeout=5)


if __name__ == "__main__":
    main()
