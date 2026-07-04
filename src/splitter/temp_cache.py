from __future__ import annotations

import atexit
import re
import shutil
import tempfile
from pathlib import Path

_CACHE_ROOT = Path(tempfile.gettempdir()) / "AudioSplitter" / "downloads"
_ACTIVE_FILES: set[Path] = set()


def cache_dir() -> Path:
    path = _CACHE_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str, *, max_length: int = 120) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip().strip(".")
    if not cleaned:
        cleaned = "download"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". ")
    return cleaned


def target_path(video_id: str, extension: str = ".mp3") -> Path:
    ext = extension if extension.startswith(".") else f".{extension}"
    return cache_dir() / f"{video_id}{ext}"


def register_active(path: Path) -> None:
    resolved = path.resolve()
    _ACTIVE_FILES.add(resolved)


def release(path: Path) -> None:
    resolved = path.resolve()
    _ACTIVE_FILES.discard(resolved)
    if resolved.exists():
        resolved.unlink()


def clear_previous_downloads(except_path: Path | None = None) -> None:
    keep = except_path.resolve() if except_path else None
    for item in cache_dir().glob("*"):
        if not item.is_file():
            continue
        resolved = item.resolve()
        if keep is not None and resolved == keep:
            continue
        if resolved in _ACTIVE_FILES:
            continue
        item.unlink(missing_ok=True)


def cleanup_on_exit() -> None:
    for path in list(_ACTIVE_FILES):
        path.unlink(missing_ok=True)
    _ACTIVE_FILES.clear()


atexit.register(cleanup_on_exit)
