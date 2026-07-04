from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_frozen_desktop() -> None:
    """Prepare pythonnet/pywebview before the GUI imports clr on Windows."""
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return

    # pywebview loads System.Windows.Forms via .NET Framework; coreclr cannot resolve it.
    os.environ.setdefault("PYTHONNET_RUNTIME", "netfx")

    root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    candidates = [Path(sys.executable)]
    for relative in ("pythonnet", "clr_loader", "webview/lib"):
        path = root / relative
        if path.is_file():
            candidates.append(path)
        elif path.is_dir():
            candidates.extend(path.rglob("*"))

    for path in candidates:
        if not path.is_file():
            continue
        zone = f"{path}:Zone.Identifier"
        try:
            os.remove(zone)
        except OSError:
            pass


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def _default_output_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path.home() / "Music" / "AudioSplitter" / "stems"
    return Path.cwd() / "stems"


def _ui_directory() -> Path:
    root = _resource_root()
    if getattr(sys, "frozen", False):
        return root / "splitter" / "desktop" / "ui"
    return root / "ui"


def main() -> None:
    _configure_frozen_desktop()

    import webview

    from splitter.desktop.api import DesktopApi

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        bundled_ffmpeg = exe_dir / "ffmpeg.exe"
        if bundled_ffmpeg.exists():
            os.environ["PATH"] = f"{exe_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    ui_dir = _ui_directory()
    index_path = ui_dir / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"Desktop UI not found at {index_path}")

    api = DesktopApi(output_root=_default_output_dir())
    window = webview.create_window(
        "Audio Splitter",
        url=index_path.as_uri(),
        js_api=api,
        width=1100,
        height=820,
        min_size=(900, 700),
    )
    webview.start(gui="edgechromium" if os.name == "nt" else None)


if __name__ == "__main__":
    main()
