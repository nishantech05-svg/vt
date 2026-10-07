# VoiceType MVP

A small Windows tray app for local English dictation. Press **Ctrl+Alt+Space** to start recording, speak, then press it again. The transcription is typed at the current cursor using Windows `SendInput`; the clipboard is left alone.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer
- A microphone
- Internet for the first model download; transcription runs locally after that

## Run from source

Open PowerShell in this folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python voice_type.py
```

The tray icon appears while the app runs. The first start downloads the `base.en` model and may take a little while. Wait for the “Ready” notification before dictating.

## Notes

- Audio is held in memory for the active recording and passed to the local model. This MVP does not save recordings.
- `base.en` is a compact English-only Whisper model. CPU int8 is used so a dedicated GPU is not required.
- The current shortcut toggles recording: first press starts, second press stops and transcribes.
- Text insertion uses Unicode keyboard events and does not modify the clipboard.
- Global keyboard hooks and synthetic typing may not work in elevated applications. Run VoiceType at the same privilege level as the app receiving text.
- Close the app from the tray menu. It must remain running to listen for its shortcut.

## MVP limits

There is no editable transcript window, automatic punctuation correction, custom vocabulary, or installer yet. The app is intended to validate the core workflow first.
