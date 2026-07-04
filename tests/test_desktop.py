from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from splitter.desktop.api import DesktopApi
from splitter.separator import SeparationOptions


def test_desktop_api_get_available_stems(tmp_path: Path) -> None:
    api = DesktopApi(output_root=tmp_path / "stems")
    assert api.get_available_stems() == ["vocals", "drums", "bass", "other"]


def test_desktop_api_start_separation_rejects_missing_file(tmp_path: Path) -> None:
    api = DesktopApi(output_root=tmp_path / "stems")
    result = api.start_separation(str(tmp_path / "missing.mp3"))
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_desktop_api_start_separation_requires_ready_state(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")

    with patch("splitter.desktop.api.validate_input_path"):
        result = api.start_separation(str(input_path))

    assert result["ok"] is False
    assert "load an audio source" in result["error"].lower()


def test_desktop_api_start_separation_rejects_custom_without_stems(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")
    api._set_loaded_input(
        input_path,
        display_name=str(input_path),
        source_type="local",
        is_temp=False,
    )

    with patch("splitter.desktop.api.validate_input_path"):
        result = api.start_separation(str(input_path), mode="custom", selected_stems=[])

    assert result["ok"] is False
    assert "at least one stem" in result["error"].lower()


def test_desktop_api_runs_separation_in_background(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")
    api._set_loaded_input(
        input_path,
        display_name=str(input_path),
        source_type="local",
        is_temp=False,
    )

    with (
        patch("splitter.desktop.api.validate_input_path"),
        patch("splitter.desktop.api.separate_file") as separate_file,
    ):
        separate_file.return_value.output_dir = tmp_path / "stems" / "tone"
        separate_file.return_value.stems = ("vocals", "drums", "bass", "other")
        result = api.start_separation(str(input_path))

    assert result["ok"] is True
    if api._thread:
        api._thread.join(timeout=2)

    status = api.get_status()
    assert status["status"] == "done"
    assert status["stems"] == ["vocals", "drums", "bass", "other"]


def test_desktop_api_passes_mode_and_selected_stems(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")
    api._set_loaded_input(
        input_path,
        display_name=str(input_path),
        source_type="local",
        is_temp=False,
    )

    with (
        patch("splitter.desktop.api.validate_input_path"),
        patch("splitter.desktop.api.separate_file") as separate_file,
    ):
        separate_file.return_value.output_dir = tmp_path / "stems" / "tone"
        separate_file.return_value.stems = ("vocals", "drums")
        result = api.start_separation(
            str(input_path),
            mode="custom",
            selected_stems=["vocals", "drums"],
        )

    assert result["ok"] is True
    if api._thread:
        api._thread.join(timeout=2)

    options = separate_file.call_args.kwargs["options"]
    assert isinstance(options, SeparationOptions)
    assert options.mode == "custom"
    assert options.selected_stems == ("vocals", "drums")


def test_desktop_api_download_youtube_sets_ready_state(tmp_path: Path) -> None:
    downloaded = tmp_path / "abc123.mp3"
    downloaded.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")

    with (
        patch("splitter.sources.youtube.fetch_metadata") as fetch_metadata,
        patch("splitter.sources.youtube.download_audio", return_value=downloaded),
        patch("splitter.desktop.api.validate_input_path"),
    ):
        from splitter.sources.youtube import VideoMetadata

        fetch_metadata.return_value = VideoMetadata(
            video_id="abc123",
            title="Test Track",
            duration=120,
        )
        result = api.download_youtube("https://www.youtube.com/watch?v=abc123")

    assert result["ok"] is True
    if api._thread:
        api._thread.join(timeout=2)

    status = api.get_status()
    assert status["status"] == "ready"
    assert status["displayName"] == "Test Track"
    assert api.get_input_uri() == downloaded.resolve().as_uri()


def test_desktop_api_get_input_uri_without_loaded_input(tmp_path: Path) -> None:
    api = DesktopApi(output_root=tmp_path / "stems")
    assert api.get_input_uri() is None
