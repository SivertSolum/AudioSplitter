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


def test_desktop_api_start_separation_rejects_custom_without_stems(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")

    with patch("splitter.desktop.api.validate_input_path"):
        result = api.start_separation(str(input_path), mode="custom", selected_stems=[])

    assert result["ok"] is False
    assert "at least one stem" in result["error"].lower()


def test_desktop_api_runs_separation_in_background(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    api = DesktopApi(output_root=tmp_path / "stems")

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
