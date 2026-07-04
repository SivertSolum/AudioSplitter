from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from demucs.audio import prevent_clip


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
