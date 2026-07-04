from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from splitter.desktop.api import DesktopApi


def test_desktop_api_start_separation_rejects_missing_file(tmp_path: Path) -> None:
    api = DesktopApi(output_root=tmp_path / "stems")
    result = api.start_separation(str(tmp_path / "missing.mp3"))
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


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
