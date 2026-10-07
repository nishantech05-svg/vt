# VoiceType

VoiceType is a menu bar dictation app. Press the global shortcut to record, press it again to stop, and the recognized words are typed at the current cursor. Speech recognition runs locally with Whisper; recordings are kept in memory and are not saved.

## Install on macOS

1. Copy this project folder to your Mac.
2. Open Terminal in the copied project folder and run `bash "Install VoiceType.command"`.
3. The installer builds and places **VoiceType.app** in `~/Applications`, then opens it. The first build downloads the app's Python dependencies.
4. On first launch, allow microphone access. In **System Settings → Privacy & Security → Accessibility**, enable VoiceType so it can listen for the global shortcut and type the transcript into other apps.
5. The first run downloads the `base.en` speech model. Once the menu bar status says **Ready**, press **Control+Option+Space** to dictate.

The Mac installer needs Python 3 on the Mac to build the self-contained app once. You do not need to start Python or a terminal to use VoiceType after installation. The generated app includes the runtime and dependencies. The first model download needs an internet connection; afterward, transcription works offline.

VoiceType does not use an API key. Recognition is local. The default shortcut is Control+Option+Space on macOS and Ctrl+Alt+Space on Windows.

## Update or remove

To rebuild after updating the project, run **Install VoiceType.command** again. To remove VoiceType, quit it from the menu bar, then delete `~/Applications/VoiceType.app`. Its downloaded model is cached by Hugging Face under `~/.cache/huggingface`; delete that cache separately if you also want to remove the model.

## Install on Windows

After building, run `dist-installer\VoiceType-Setup.exe`, choose whether to add a desktop shortcut or launch VoiceType when you sign in, and finish setup. The installer adds VoiceType to the Start menu. Allow microphone access if Windows asks. The first launch downloads the local speech model and needs an internet connection; later transcription works offline. VoiceType does not need an API key.

To build `VoiceType-Setup.exe` from this project on a Windows build machine:

1. Install Python 3.11 or newer (64-bit) and Inno Setup 6 or 7.
2. Run `Windows_Installer.ps1` from PowerShell. The build script creates an isolated environment, bundles the runtime with PyInstaller, then creates `dist-installer\VoiceType-Setup.exe`.

The installer is per-user and does not need administrator permission. The optional sign-in launch setting is for the current Windows user.

### Windows mini player (0.2.0)

VoiceType opens a small floating panel at the bottom-right, above the taskbar. It shows loading/recording status immediately, with Start and Stop buttons and the latest transcript. The transcript appears after Stop, rather than live while speaking. You can also toggle recording with Ctrl+Alt+Space.

The panel stays above other windows without taking keyboard focus. Select your target document before recording; if you switch to another window before transcription finishes, VoiceType keeps the transcript in the panel instead of typing into the wrong window. Closing the panel quits VoiceType; minimizing keeps the shortcut available. Opening VoiceType again restores the existing panel, including while the speech engine is loading.

When upgrading from 0.1.0, quit all old VoiceType tray instances before installing 0.2.0. Those old processes do not have the instance lock. The new installer also asks running copies to close during an update.

## Build the Mac app manually

On a Mac with Python 3 installed, run:

```sh
python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm voice_type.spec
```

The app bundle is written to `dist/VoiceType.app`. Build on the Mac architecture you intend to use. The app is not signed or notarized for public distribution, so macOS may require **Open Anyway** in Privacy & Security for locally built copies.

## Notes

- `base.en` is English-only. CPU inference is used for compatibility.
- Text insertion uses synthetic keyboard events and does not change the clipboard.
- Global keyboard monitoring and simulated typing require macOS Accessibility permission. They may not work in elevated or protected applications.
- On Windows, close the mini player to quit. On Mac, use the menu bar Quit item. The app must remain running to listen for its shortcut.

## MVP limits

There is no editable transcript window, custom vocabulary, or in-app shortcut editor yet.
