from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import torch

DeviceChoice = Literal["auto", "cpu", "cuda"]
ModelName = Literal["htdemucs", "htdemucs_ft"]

DEFAULT_MODEL: ModelName = "htdemucs_ft"
SUPPORTED_MODELS: tuple[ModelName, ...] = ("htdemucs", "htdemucs_ft")
FOUR_STEM_OUTPUTS = ("vocals", "drums", "bass", "other")
TWO_STEM_SOURCES = FOUR_STEM_OUTPUTS


@dataclass(frozen=True)
class ResolvedDevice:
    choice: DeviceChoice
    torch_device: str
    cuda_available: bool


def resolve_device(choice: DeviceChoice) -> ResolvedDevice:
    cuda_available = torch.cuda.is_available()

    if choice == "auto":
        torch_device = "cuda" if cuda_available else "cpu"
    elif choice == "cuda":
        if not cuda_available:
            raise RuntimeError(
                "CUDA was requested but no GPU is available. "
                "Use --device cpu or --device auto."
            )
        torch_device = "cuda"
    else:
        torch_device = "cpu"

    return ResolvedDevice(choice=choice, torch_device=torch_device, cuda_available=cuda_available)
