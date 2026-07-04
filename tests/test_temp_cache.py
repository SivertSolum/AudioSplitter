from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from splitter.temp_cache import (
    cache_dir,
    clear_previous_downloads,
    register_active,
    release,
    sanitize_filename,
    target_path,
)


def test_cache_dir_creates_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("splitter.temp_cache._CACHE_ROOT", tmp_path / "downloads")
    path = cache_dir()
    assert path.exists()
    assert path.is_dir()


def test_sanitize_filename_removes_invalid_chars() -> None:
    assert sanitize_filename('My: Song / "Test"') == 'My Song  Test'


def test_sanitize_filename_fallback_for_empty() -> None:
    assert sanitize_filename(":::") == "download"


def test_target_path_uses_video_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("splitter.temp_cache._CACHE_ROOT", tmp_path)
    assert target_path("abc123") == tmp_path / "abc123.mp3"


def test_register_and_release(tmp_path: Path) -> None:
    file_path = tmp_path / "track.mp3"
    file_path.write_bytes(b"audio")
    register_active(file_path)
    release(file_path)
    assert not file_path.exists()


def test_clear_previous_downloads_keeps_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("splitter.temp_cache._CACHE_ROOT", tmp_path)
    keep = tmp_path / "keep.mp3"
    remove = tmp_path / "remove.mp3"
    keep.write_bytes(b"a")
    remove.write_bytes(b"b")
    clear_previous_downloads(except_path=keep)
    assert keep.exists()
    assert not remove.exists()
