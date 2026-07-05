# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
project_root = Path(SPECPATH).resolve().parent
hooks_dir = project_root / "build" / "hooks"
ui_src = project_root / "src" / "splitter" / "desktop" / "ui"
icon_src = ui_src / "audiosplitter-icon.ico"

# Do not exclude torch.* or torchaudio.* subpackages — both libraries import many
# submodules at package init (e.g. torchaudio.datasets). Optional third-party only.
TORCH_EXCLUDES = [
    "torch.utils.tensorboard",
    "tensorboard",
    "torchvision",
    "torchtext",
    "torchdata",
    "torchaudio.prototype",
    "demucs.train",
    "demucs.evaluate",
    "demucs.solver",
    "demucs.augment",
    "demucs.distrib",
    "demucs.repitch",
    "demucs.wdemucs",
    "demucs.separate",
    "demucs.__main__",
    "matplotlib",
    "scipy",
    "pandas",
    "IPython",
    "notebook",
    "numba",
]

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
    "numpy",
    "numpy.core.multiarray",
    "numpy._core._multiarray_umath",
    "demucs",
    "demucs.pretrained",
    "demucs.audio",
    "demucs.apply",
    "demucs.htdemucs",
    "dora",
    "einops",
    "julius",
    "lameenc",
    "openunmix",
    "yaml",
    "tqdm",
    "torch",
    "torch.cuda",
    "torch.distributed",
    "torch.nn",
    "torch.nn.functional",
    "torchaudio",
]

for package in ("webview", "pythonnet", "clr_loader"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports = list(dict.fromkeys(hiddenimports))

a = Analysis(
    [str(project_root / "src" / "splitter" / "desktop" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(hooks_dir)],
    hooksconfig={},
    runtime_hooks=[str(project_root / "build" / "pywebview_runtime_hook.py")],
    excludes=TORCH_EXCLUDES,
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
