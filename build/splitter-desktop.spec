# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
project_root = Path(SPECPATH).resolve().parent
ui_src = project_root / "src" / "splitter" / "desktop" / "ui"
icon_src = ui_src / "audiosplitter-icon.ico"

datas = [(str(ui_src), "splitter/desktop/ui")]
binaries = []
hiddenimports = [
    "webview",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr_loader",
    "clr_loader.ffi",
    "clr_loader.netfx",
    "pythonnet",
    "splitter.desktop.api",
    "splitter.separator",
    "splitter.models",
    "splitter.audio_io",
    "splitter.sources.youtube",
    "splitter.temp_cache",
    "yt_dlp",
    "demucs",
    "demucs.pretrained",
    "demucs.audio",
    "demucs.apply",
    "demucs.htdemucs",
    "demucs.audio_legacy",
    "torch",
    "torchaudio",
]

for package in ("webview", "pythonnet", "clr_loader", "torch", "torchaudio", "demucs"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    [str(project_root / "src" / "splitter" / "desktop" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / "build" / "pywebview_runtime_hook.py")],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AudioSplitter",
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
    icon=str(icon_src) if icon_src.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AudioSplitter",
)
