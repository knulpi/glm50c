"""TTS worker: loads the Piper voice once, speaks texts from a queue."""

import io
import queue
import subprocess
import sys
import threading
import wave
from pathlib import Path

LINUX_PLAYERS = (["pw-play", "-"], ["paplay"], ["aplay", "-q"])


def play_wav(wav_bytes: bytes, ui: dict) -> None:
    if sys.platform == "win32":
        import winsound

        winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
        return
    if sys.platform == "darwin":
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            f.write(wav_bytes)
            f.flush()
            subprocess.run(["afplay", f.name], check=False)
        return
    for player in LINUX_PLAYERS:
        try:
            subprocess.run(player, input=wav_bytes, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    players = "/".join(p[0] for p in LINUX_PLAYERS)
    print(ui["no_audio_player"].format(players=players), file=sys.stderr)


class Speaker(threading.Thread):
    def __init__(self, voice_path: Path, ui: dict):
        super().__init__(daemon=True)
        self.queue: queue.Queue[str | None] = queue.Queue()
        self.voice_path = voice_path
        self.ui = ui
        self.voice = None

    def run(self):
        from piper import PiperVoice  # lazy: keeps onnxruntime out of tests

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
                play_wav(buf.read(), self.ui)
            except Exception as e:
                print(self.ui["tts_error"].format(error=e), file=sys.stderr)

    def say(self, text: str):
        self.queue.put(text)

    def shutdown(self, timeout: float = 5):
        self.queue.put(None)
        self.join(timeout=timeout)
