"""Focused Windows regression checks; no microphone or model download required."""
import ctypes
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@unittest.skipUnless(sys.platform == "win32", "Windows runtime")
class WindowsRuntimeTests(unittest.TestCase):
    def test_other_process_cannot_become_primary_and_requests_existing_panel(self):
        from windows_app import InstanceLock, k
        name = "VoiceType.Test." + uuid.uuid4().hex
        first = InstanceLock(name)
        try:
            self.assertTrue(first.primary)
            script = ("from windows_app import InstanceLock; "
                      f"lock=InstanceLock({name!r}); "
                      "assert not lock.primary; lock.close()")
            subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True, timeout=15)
            self.assertEqual(k.WaitForSingleObject(first.wake, 0), 0)
        finally:
            first.close()
        fresh = InstanceLock(name)
        try:
            self.assertTrue(fresh.primary)
        finally:
            fresh.close()

    def test_panel_can_display_transcript_without_loading_speech_libraries(self):
        from windows_app import InstanceLock, Player, u
        lock = InstanceLock("VoiceType.PanelTest." + uuid.uuid4().hex)
        player = Player(lock, show=False)
        try:
            self.assertIsNone(player.engine)
            player.events.put(("transcript", "Words captured from speech."))
            player.pump()
            get_text = u.GetWindowTextW
            get_text.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
            buffer = ctypes.create_unicode_buffer(100)
            get_text(player.controls[12], buffer, len(buffer))
            self.assertEqual(buffer.value, "Words captured from speech.")
        finally:
            u.DestroyWindow(player.hwnd)
            lock.close()

    def test_transcript_is_kept_when_insertion_fails_and_busy_state_clears(self):
        from voice_type import VoiceType, INPUT
        self.assertEqual(ctypes.sizeof(INPUT), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        transcripts, statuses = [], []
        def blocked_insertion(text):
            raise RuntimeError("Focus changed")
        engine = VoiceType(statuses.append, transcripts.append, blocked_insertion)
        engine._model = SimpleNamespace(transcribe=lambda *a, **kw: ([SimpleNamespace(text=" Hello ")], None))
        engine._transcribing = True
        engine._transcribe_and_type(None)
        self.assertEqual(transcripts, ["Hello"])
        self.assertIn("Focus changed", statuses[-1])
        self.assertFalse(engine._transcribing)


if __name__ == "__main__":
    unittest.main()
