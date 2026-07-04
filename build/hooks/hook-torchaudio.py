# Minimal torchaudio hook — include subpackages imported by torchaudio.__init__.

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

binaries = collect_dynamic_libs("torchaudio")
module_collection_mode = "pyz+py"

hiddenimports = [
    "torchaudio",
    "torchaudio._extension",
    "torchaudio.backend",
    "torchaudio.backend.common",
    "torchaudio.backend.soundfile_backend",
    "torchaudio.backend.sox_io_backend",
    "torchaudio.compliance",
    "torchaudio.datasets",
    "torchaudio.functional",
    "torchaudio.io",
    "torchaudio.models",
    "torchaudio.pipelines",
    "torchaudio.transforms",
    "torchaudio.utils",
] + collect_submodules("torchaudio.lib")
