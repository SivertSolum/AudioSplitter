from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import torch
from demucs.apply import BagOfModels, apply_model
from demucs.htdemucs import HTDemucs
from demucs.pretrained import get_model
from demucs.separate import load_track

from splitter.audio_io import save_wav

from splitter.models import DEFAULT_MODEL, FOUR_STEM_OUTPUTS, ModelName, resolve_device


AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}


@dataclass(frozen=True)
class SeparationResult:
    input_path: Path
    output_dir: Path
    stems: tuple[str, ...]


@dataclass(frozen=True)
class SeparationOptions:
    model: ModelName = DEFAULT_MODEL
    device: str = "auto"
    two_stems: str | None = None
    progress: bool = True
    shifts: int = 1
    overlap: float = 0.25


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def needs_ffmpeg(path: Path) -> bool:
    return path.suffix.lower() != ".wav"


def validate_input_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(AUDIO_EXTENSIONS))
        raise ValueError(f"Unsupported audio format '{path.suffix}'. Supported: {supported}")
    if needs_ffmpeg(path) and not ffmpeg_available():
        raise RuntimeError(
            f"ffmpeg is required to decode {path.suffix} files but was not found on PATH. "
            "Install ffmpeg and ensure it is available in your terminal."
        )


def iter_audio_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Input directory not found: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Input path is not a directory: {directory}")

    files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not files:
        raise ValueError(f"No supported audio files found in {directory}")
    return files


def _validate_two_stems(selected: str, model_sources: list[str]) -> None:
    if selected not in model_sources:
        raise ValueError(
            f"Invalid two-stem source '{selected}'. Choose one of: {', '.join(model_sources)}"
        )


def _run_model(
    model,
    wav: torch.Tensor,
    *,
    device: str,
    options: SeparationOptions,
) -> torch.Tensor:
    ref = wav.mean(0)
    normalized = wav.clone()
    normalized -= ref.mean()
    normalized /= ref.std()

    sources = apply_model(
        model,
        normalized[None],
        device=device,
        shifts=options.shifts,
        split=True,
        overlap=options.overlap,
        progress=options.progress,
    )[0]

    sources *= ref.std()
    sources += ref.mean()
    return sources


def _save_stems(
    sources: torch.Tensor,
    source_names: list[str],
    output_dir: Path,
    *,
    samplerate: int,
    two_stems: str | None,
) -> tuple[str, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)

    if two_stems is None:
        written: list[str] = []
        for source, name in zip(sources, source_names, strict=True):
            save_wav(source, output_dir / f"{name}.wav", samplerate)
            written.append(name)
        return tuple(written)

    _validate_two_stems(two_stems, source_names)
    selected_index = source_names.index(two_stems)
    remaining = [sources[index] for index, name in enumerate(source_names) if name != two_stems]

    save_wav(sources[selected_index], output_dir / f"{two_stems}.wav", samplerate)
    other_stem = torch.zeros_like(sources[0])
    for stem in remaining:
        other_stem += stem
    save_wav(other_stem, output_dir / f"no_{two_stems}.wav", samplerate)
    return (two_stems, f"no_{two_stems}")


def separate_file(
    input_path: Path,
    output_dir: Path,
    *,
    options: SeparationOptions | None = None,
) -> SeparationResult:
    options = options or SeparationOptions()
    validate_input_path(input_path)

    resolved = resolve_device(options.device)  # type: ignore[arg-type]
    track_dir = output_dir / input_path.stem

    model = get_model(options.model)
    model.cpu()
    model.eval()

    if options.two_stems:
        _validate_two_stems(options.two_stems, list(model.sources))

    if isinstance(model, HTDemucs):
        _ = model.segment
    elif isinstance(model, BagOfModels):
        _ = model.max_allowed_segment

    wav = load_track(input_path, model.audio_channels, model.samplerate)
    sources = _run_model(model, wav, device=resolved.torch_device, options=options)
    written_stems = _save_stems(
        sources,
        list(model.sources),
        track_dir,
        samplerate=model.samplerate,
        two_stems=options.two_stems,
    )

    return SeparationResult(
        input_path=input_path,
        output_dir=track_dir,
        stems=written_stems,
    )


def separate_many(
    input_paths: Iterable[Path],
    output_dir: Path,
    *,
    options: SeparationOptions | None = None,
) -> list[SeparationResult]:
    results: list[SeparationResult] = []
    for input_path in input_paths:
        results.append(separate_file(input_path, output_dir, options=options))
    return results
