"""Minimal Windows dictation tray app using local faster-whisper transcription."""

from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes
from typing import Optional

if sys.platform != "win32":
    raise SystemExit("VoiceType MVP currently supports Windows 10/11 only.")

import keyboard
import numpy as np
import pystray
import sounddevice as sd
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw


HOTKEY = "ctrl+alt+space"
SAMPLE_RATE = 16_000
MODEL_NAME = "base.en"

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


def type_at_cursor(text: str) -> None:
    """Type Unicode text through Windows SendInput without changing clipboard."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    send_input = user32.SendInput
    send_input.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    send_input.restype = wintypes.UINT

    # SendInput's Unicode mode takes UTF-16 code units, including surrogate pairs.
    units = text.encode("utf-16-le", errors="replace")
    for offset in range(0, len(units), 2):
        code_unit = int.from_bytes(units[offset : offset + 2], "little")
        events = (INPUT * 2)()
        events[0].type = INPUT_KEYBOARD
        events[0].union.ki = KEYBDINPUT(0, code_unit, KEYEVENTF_UNICODE, 0, 0)
        events[1].type = INPUT_KEYBOARD
        events[1].union.ki = KEYBDINPUT(
            0, code_unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0
        )
        sent = send_input(2, events, ctypes.sizeof(INPUT))
        if sent != 2:
            raise ctypes.WinError(ctypes.get_last_error())


class VoiceType:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._model: Optional[WhisperModel] = None
        self._transcribing = False
        self._status = "Loading local model…"
        self._icon: Optional[pystray.Icon] = None

    def _set_status(self, status: str, notify: bool = False) -> None:
        self._status = status
        if self._icon:
            self._icon.title = f"VoiceType — {status}"
            if notify:
                self._icon.notify(status, "VoiceType")

    def _load_model(self) -> None:
        try:
            # CPU int8 keeps the first version usable without a dedicated GPU.
            self._model = WhisperModel(
                MODEL_NAME, device="cpu", compute_type="int8", cpu_threads=4
            )
            self._set_status("Ready. Press Ctrl+Alt+Space to dictate.", notify=True)
        except Exception as exc:
            self._set_status(f"Model error: {exc}", notify=True)

    def _audio_callback(self, indata: np.ndarray, frames: int, timing: object, status: object) -> None:
        if status:
            # Audio dropouts are recoverable; the next callback continues recording.
            pass
        with self._lock:
            self._frames.append(indata[:, 0].copy())

    def toggle_recording(self) -> None:
        if self._model is None:
            self._set_status("Model is still loading. Try again in a moment.", notify=True)
            return
        if self._transcribing:
            self._set_status("Transcribing… wait for the text to appear.", notify=True)
            return

        if self._stream is None:
            try:
                with self._lock:
                    self._frames.clear()
                stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                stream.start()
                self._stream = stream
                self._set_status("Recording… press Ctrl+Alt+Space to finish.", notify=True)
            except Exception as exc:
                self._set_status(f"Microphone error: {exc}", notify=True)
            return

        stream, self._stream = self._stream, None
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        with self._lock:
            audio = np.concatenate(self._frames) if self._frames else np.array([], dtype=np.float32)
            self._frames.clear()
        if audio.size < SAMPLE_RATE // 4:
            self._set_status("No speech captured. Press the shortcut to try again.", notify=True)
            return
        self._set_status("Transcribing locally…", notify=True)
        self._transcribing = True
        threading.Thread(target=self._transcribe_and_type, args=(audio,), daemon=True).start()

    def _transcribe_and_type(self, audio: np.ndarray) -> None:
        try:
            assert self._model is not None
            segments, _ = self._model.transcribe(
                audio,
                language="en",
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if not text:
                self._set_status("No speech recognized. Press the shortcut to try again.", notify=True)
                return
            type_at_cursor(text)
            self._set_status("Ready. Press Ctrl+Alt+Space to dictate.", notify=True)
        except Exception as exc:
            self._set_status(f"Transcription or typing error: {exc}", notify=True)
        finally:
            self._transcribing = False

    @staticmethod
    def _make_icon() -> Image.Image:
        image = Image.new("RGB", (64, 64), "#202938")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((23, 10, 41, 39), radius=9, fill="#8bd5ca")
        draw.arc((14, 20, 50, 51), 0, 180, fill="white", width=4)
        draw.line((32, 49, 32, 56), fill="white", width=4)
        draw.line((23, 56, 41, 56), fill="white", width=4)
        return image

    def run(self) -> None:
        self._icon = pystray.Icon(
            "VoiceType",
            self._make_icon(),
            "VoiceType — Loading local model…",
            menu=pystray.Menu(
                pystray.MenuItem("Ctrl+Alt+Space: start/stop dictation", None, enabled=False),
                pystray.MenuItem("Quit VoiceType", lambda icon, item: icon.stop()),
            ),
        )
        keyboard.add_hotkey(HOTKEY, self.toggle_recording, suppress=False)
        threading.Thread(target=self._load_model, daemon=True).start()
        try:
            self._icon.run()
        finally:
            keyboard.remove_hotkey(HOTKEY)
            if self._stream:
                self._stream.stop()
                self._stream.close()


if __name__ == "__main__":
    VoiceType().run()
