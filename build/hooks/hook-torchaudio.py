# Minimal torchaudio hook — include subpackages for torchaudio 2.x (backend/io removed).

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

binaries = collect_dynamic_libs("torchaudio")
module_collection_mode = "pyz+py"

hiddenimports = [
    "torchaudio",
    "torchaudio._extension",
    "torchaudio._internal",
    "torchaudio.compliance",
    "torchaudio.datasets",
    "torchaudio.functional",
    "torchaudio.models",
    "torchaudio.pipelines",
    "torchaudio.transforms",
    "torchaudio.utils",
] + collect_submodules("torchaudio.lib")
