from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from splitter.sources.youtube import (
    VideoMetadata,
    check_download_size,
    download_audio,
    fetch_metadata,
    validate_youtube_url,
)


def test_validate_youtube_url_accepts_watch_link() -> None:
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert validate_youtube_url(url) == url


def test_validate_youtube_url_accepts_short_link() -> None:
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert validate_youtube_url(url) == url


def test_validate_youtube_url_rejects_non_youtube() -> None:
    with pytest.raises(ValueError, match="valid YouTube"):
        validate_youtube_url("https://example.com/video")


def test_check_download_size_rejects_long_video() -> None:
    with pytest.raises(ValueError, match="exceeds the 50 MB limit"):
        check_download_size(60 * 60)


def test_fetch_metadata_returns_video_metadata() -> None:
    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.extract_info.return_value = {
        "id": "abc123",
        "title": "Test Song",
        "duration": 180,
    }

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        metadata = fetch_metadata("https://www.youtube.com/watch?v=abc123")

    assert metadata == VideoMetadata(video_id="abc123", title="Test Song", duration=180)


def test_download_audio_uses_cached_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("splitter.temp_cache._CACHE_ROOT", tmp_path)
    cached = tmp_path / "abc123.mp3"
    cached.write_bytes(b"RIFF")

    with (
        patch("splitter.sources.youtube.fetch_metadata") as fetch_metadata_mock,
        patch("splitter.sources.youtube.validate_input_path"),
        patch("yt_dlp.YoutubeDL") as ydl_cls,
    ):
        fetch_metadata_mock.return_value = VideoMetadata(
            video_id="abc123",
            title="Cached",
            duration=60,
        )
        result = download_audio("https://www.youtube.com/watch?v=abc123")

    assert result == cached
    ydl_cls.assert_not_called()


def test_download_audio_downloads_when_cache_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("splitter.temp_cache._CACHE_ROOT", tmp_path)

    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl

    def _download(_urls: list[str]) -> None:
        (tmp_path / "abc123.mp3").write_bytes(b"RIFF")

    mock_ydl.download.side_effect = _download

    with (
        patch("splitter.sources.youtube.fetch_metadata") as fetch_metadata_mock,
        patch("splitter.sources.youtube.validate_input_path"),
        patch("yt_dlp.YoutubeDL", return_value=mock_ydl),
    ):
        fetch_metadata_mock.return_value = VideoMetadata(
            video_id="abc123",
            title="Fresh",
            duration=60,
        )
        result = download_audio("https://www.youtube.com/watch?v=abc123")

    assert result == tmp_path / "abc123.mp3"
    mock_ydl.download.assert_called_once()


def test_download_audio_requires_yt_dlp() -> None:
    with patch(
        "splitter.sources.youtube._require_yt_dlp",
        side_effect=RuntimeError("yt-dlp is required for YouTube downloads."),
    ):
        with pytest.raises(RuntimeError, match="yt-dlp is required"):
            fetch_metadata("https://www.youtube.com/watch?v=abc123")
