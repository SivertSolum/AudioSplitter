from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import torch
from demucs.audio import prevent_clip

EXPORT_AUDIO_EXTENSIONS = frozenset({".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aac", ".wma"})


def save_wav(stem: torch.Tensor, path: Path, samplerate: int, *, clip: str = "rescale") -> None:
    """Save a (channels, samples) float tensor as 16-bit PCM WAV."""
    wav = prevent_clip(stem, mode=clip)
    data = wav.detach().cpu().numpy()
    if data.ndim == 1:
        data = data[None, :]

    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(data.T, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)

    import wave

    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(data.shape[0])
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        handle.writeframes(pcm.tobytes())


def export_audio_file(source_wav: Path, destination: Path) -> None:
    """Copy or transcode a WAV stem to another supported audio format."""
    suffix = destination.suffix.lower()
    if suffix not in EXPORT_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(EXPORT_AUDIO_EXTENSIONS))
        raise ValueError(f"Unsupported export format '{suffix}'. Supported: {supported}")
    if not source_wav.exists():
        raise FileNotFoundError(f"Source audio not found: {source_wav}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".wav":
        shutil.copy2(source_wav, destination)
        return

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            f"ffmpeg is required to export audio as {suffix} but was not found on PATH."
        )

    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-i", str(source_wav), str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise RuntimeError(f"Could not export audio: {detail}")
