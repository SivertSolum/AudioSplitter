from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch
from typer.testing import CliRunner

from splitter.cli import app
from splitter.models import resolve_device
from splitter.separator import SeparationOptions, validate_input_path

runner = CliRunner()


def test_resolve_device_auto_uses_cpu_when_cuda_unavailable() -> None:
    with patch("splitter.models.torch.cuda.is_available", return_value=False):
        resolved = resolve_device("auto")
    assert resolved.torch_device == "cpu"


def test_resolve_device_cuda_raises_without_gpu() -> None:
    with patch("splitter.models.torch.cuda.is_available", return_value=False):
        with pytest.raises(RuntimeError, match="CUDA was requested"):
            resolve_device("cuda")


def test_validate_input_path_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.wav"
    with pytest.raises(FileNotFoundError, match="not found"):
        validate_input_path(missing)


def test_validate_input_path_unsupported_extension(tmp_path: Path) -> None:
    bad_file = tmp_path / "track.txt"
    bad_file.write_text("not audio", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported audio format"):
        validate_input_path(bad_file)


def test_validate_file_size_rejects_large_file(tmp_path: Path) -> None:
    from splitter.separator import validate_file_size

    large_file = tmp_path / "large.wav"
    large_file.write_bytes(b"\x00" * (51 * 1024 * 1024))
    with pytest.raises(ValueError, match="exceeds the 50 MB limit"):
        validate_file_size(large_file, max_mb=50)


def test_validate_input_path_enforces_size_when_requested(tmp_path: Path) -> None:
    large_file = tmp_path / "large.wav"
    large_file.write_bytes(b"\x00" * (51 * 1024 * 1024))
    with pytest.raises(ValueError, match="exceeds the 50 MB limit"):
        validate_input_path(large_file, max_mb=50)


def test_cli_info_runs() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Splitter v" in result.stdout
    assert "htdemucs_ft" in result.stdout
    assert "full" in result.stdout
    assert "vocal_split" in result.stdout
    assert "custom" in result.stdout
    assert "vocals" in result.stdout


def test_cli_split_custom_without_stems_fails(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")
    result = runner.invoke(app, ["split", str(input_path), "--mode", "custom"])
    assert result.exit_code == 1
    assert "requires --stems" in result.stdout


def test_cli_split_vocal_split_mode(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    with patch("splitter.cli.separate_file") as separate_file:
        separate_file.return_value.output_dir = tmp_path / "stems" / "tone"
        separate_file.return_value.stems = ("vocals", "no_vocals")
        result = runner.invoke(app, ["split", str(input_path), "--mode", "vocal_split"])

    assert result.exit_code == 0
    options = separate_file.call_args.kwargs["options"]
    assert options.mode == "vocal_split"


def test_cli_split_custom_mode(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    input_path.write_bytes(b"RIFF")

    with patch("splitter.cli.separate_file") as separate_file:
        separate_file.return_value.output_dir = tmp_path / "stems" / "tone"
        separate_file.return_value.stems = ("vocals", "bass")
        result = runner.invoke(
            app,
            ["split", str(input_path), "--mode", "custom", "--stems", "vocals,bass"],
        )

    assert result.exit_code == 0
    options = separate_file.call_args.kwargs["options"]
    assert options.mode == "custom"
    assert options.selected_stems == ("vocals", "bass")


def test_cli_split_missing_file() -> None:
    result = runner.invoke(app, ["split", "does-not-exist.mp3"])
    assert result.exit_code == 1
    assert "Error:" in result.stdout


@pytest.mark.slow
def test_separate_file_writes_stems(tmp_path: Path) -> None:
    input_path = tmp_path / "tone.wav"
    sample_rate = 44100
    seconds = 2
    t = torch.linspace(0, seconds, sample_rate * seconds)
    waveform = torch.stack([torch.sin(2 * torch.pi * 440 * t)] * 2)

    from splitter.audio_io import save_wav

    save_wav(waveform, input_path, sample_rate)

    fake_sources = torch.stack(
        [
            waveform * 0.5,
            waveform * 0.25,
            waveform * 0.1,
            waveform,
        ]
    )
    mock_model = MagicMock()
    mock_model.sources = ["drums", "bass", "other", "vocals"]
    mock_model.audio_channels = 2
    mock_model.samplerate = sample_rate

    output_dir = tmp_path / "stems"

    with (
        patch("splitter.separator.get_model", return_value=mock_model),
        patch("splitter.separator.load_track", return_value=waveform),
        patch("splitter.separator.apply_model", return_value=fake_sources[None]),
        patch("splitter.separator.save_wav") as save_wav_mock,
    ):
        from splitter.separator import separate_file

        result = separate_file(
            input_path,
            output_dir,
            options=SeparationOptions(model="htdemucs", device="cpu", progress=False),
        )

    assert result.output_dir == output_dir / "tone"
    assert result.stems == ("drums", "bass", "other", "vocals")
    assert save_wav_mock.call_count == 4


@pytest.mark.slow
def test_separate_file_vocal_split_mode(tmp_path: Path) -> None:
    input_path, output_dir = _prepare_separate_file_fixture(tmp_path)

    with _mock_separation_pipeline() as save_wav_mock:
        from splitter.separator import separate_file

        result = separate_file(
            input_path,
            output_dir,
            options=SeparationOptions(
                model="htdemucs",
                device="cpu",
                mode="vocal_split",
                progress=False,
            ),
        )

    assert result.stems == ("vocals", "no_vocals")
    assert save_wav_mock.call_count == 2


@pytest.mark.slow
def test_separate_file_custom_mode(tmp_path: Path) -> None:
    input_path, output_dir = _prepare_separate_file_fixture(tmp_path)

    with _mock_separation_pipeline() as save_wav_mock:
        from splitter.separator import separate_file

        result = separate_file(
            input_path,
            output_dir,
            options=SeparationOptions(
                model="htdemucs",
                device="cpu",
                mode="custom",
                selected_stems=("vocals", "drums"),
                progress=False,
            ),
        )

    assert result.stems == ("vocals", "drums")
    assert save_wav_mock.call_count == 2


def test_separate_file_custom_empty_raises(tmp_path: Path) -> None:
    input_path, output_dir = _prepare_separate_file_fixture(tmp_path)

    with _mock_separation_pipeline():
        from splitter.separator import separate_file

        with pytest.raises(ValueError, match="at least one stem"):
            separate_file(
                input_path,
                output_dir,
                options=SeparationOptions(
                    model="htdemucs",
                    device="cpu",
                    mode="custom",
                    selected_stems=(),
                    progress=False,
                ),
            )


def test_separate_file_custom_invalid_stem_raises(tmp_path: Path) -> None:
    input_path, output_dir = _prepare_separate_file_fixture(tmp_path)

    with _mock_separation_pipeline():
        from splitter.separator import separate_file

        with pytest.raises(ValueError, match="Invalid stem"):
            separate_file(
                input_path,
                output_dir,
                options=SeparationOptions(
                    model="htdemucs",
                    device="cpu",
                    mode="custom",
                    selected_stems=("guitar",),
                    progress=False,
                ),
            )


def _prepare_separate_file_fixture(tmp_path: Path) -> tuple[Path, Path]:
    input_path = tmp_path / "tone.wav"
    sample_rate = 44100
    seconds = 2
    t = torch.linspace(0, seconds, sample_rate * seconds)
    waveform = torch.stack([torch.sin(2 * torch.pi * 440 * t)] * 2)

    from splitter.audio_io import save_wav

    save_wav(waveform, input_path, sample_rate)
    return input_path, tmp_path / "stems"


def _mock_separation_pipeline():
    sample_rate = 44100
    seconds = 2
    t = torch.linspace(0, seconds, sample_rate * seconds)
    waveform = torch.stack([torch.sin(2 * torch.pi * 440 * t)] * 2)
    fake_sources = torch.stack(
        [
            waveform * 0.5,
            waveform * 0.25,
            waveform * 0.1,
            waveform,
        ]
    )
    mock_model = MagicMock()
    mock_model.sources = ["drums", "bass", "other", "vocals"]
    mock_model.audio_channels = 2
    mock_model.samplerate = sample_rate

    @contextmanager
    def _pipeline():
        with (
            patch("splitter.separator.get_model", return_value=mock_model),
            patch("splitter.separator.load_track", return_value=waveform),
            patch("splitter.separator.apply_model", return_value=fake_sources[None]),
            patch("splitter.separator.save_wav") as save_wav_mock,
        ):
            yield save_wav_mock

    return _pipeline()
