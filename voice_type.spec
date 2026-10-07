# PyInstaller build definition. Run this on the Mac that will use the app.
from PyInstaller.utils.hooks import collect_all

whisper_datas, whisper_binaries, whisper_hidden = collect_all("faster_whisper")
ct2_datas, ct2_binaries, ct2_hidden = collect_all("ctranslate2")
av_datas, av_binaries, av_hidden = collect_all("av")

a = Analysis(
    ["voice_type.py"],
    pathex=[],
    binaries=whisper_binaries + ct2_binaries + av_binaries,
    datas=whisper_datas + ct2_datas + av_datas,
    hiddenimports=whisper_hidden + ct2_hidden + av_hidden + ["pystray._darwin"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VoiceType",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VoiceType",
)
app = BUNDLE(
    coll,
    name="VoiceType.app",
    icon=None,
    bundle_identifier="com.voicetype.app",
    info_plist={
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": "VoiceType needs microphone access to record dictation.",
    },
)
