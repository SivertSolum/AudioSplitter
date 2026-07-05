# Minimal demucs hook — inference modules and remote model metadata only.

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("demucs")

hiddenimports = [
    "demucs",
    "demucs.apply",
    "demucs.audio",
    "demucs.demucs",
    "demucs.hdemucs",
    "demucs.htdemucs",
    "demucs.pretrained",
    "demucs.repo",
    "demucs.spec",
    "demucs.states",
    "demucs.transformer",
    "demucs.utils",
    # Demucs runtime dependencies (installed separately with --no-deps).
    "dora",
    "einops",
    "julius",
    "lameenc",
    "openunmix",
    "yaml",
    "tqdm",
]
