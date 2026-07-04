from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
import typer
from rich.console import Console
from rich.table import Table

from splitter import __version__
from splitter.models import (
    DEFAULT_MODEL,
    DEFAULT_SEPARATION_MODE,
    FOUR_STEM_OUTPUTS,
    SUPPORTED_MODELS,
    SUPPORTED_SEPARATION_MODES,
    TWO_STEM_SOURCES,
    DeviceChoice,
    ModelName,
    SeparationMode,
    resolve_device,
)
from splitter.separator import (
    SeparationOptions,
    ffmpeg_available,
    iter_audio_files,
    separate_file,
    separate_many,
)

app = typer.Typer(
    name="splitter",
    help="Split mixed audio into vocals, drums, bass, and other stems.",
    no_args_is_help=True,
)
console = Console()


def _print_device_warning(resolved) -> None:
    if resolved.torch_device == "cpu" and resolved.choice in ("auto", "cpu"):
        console.print(
            "[yellow]Running on CPU. Separation can take several minutes per track. "
            "Use an NVIDIA GPU with CUDA for faster results, or --model htdemucs for previews.[/yellow]"
        )


def _parse_stems_option(stems: Optional[str]) -> tuple[str, ...] | None:
    if stems is None:
        return None
    parsed = tuple(part.strip() for part in stems.split(",") if part.strip())
    if not parsed:
        raise ValueError("Custom mode requires at least one stem in --stems.")
    return parsed


def _run_split(
    input_path: Path,
    output_dir: Path,
    model: ModelName,
    device: DeviceChoice,
    mode: SeparationMode,
    selected_stems: tuple[str, ...] | None,
    two_stems: Optional[str],
) -> None:
    resolved = resolve_device(device)
    _print_device_warning(resolved)

    options = SeparationOptions(
        model=model,
        device=device,
        mode=mode,
        selected_stems=selected_stems,
        two_stems=two_stems,
        progress=True,
    )

    console.print(f"[bold]Model:[/bold] {model}")
    console.print(f"[bold]Device:[/bold] {resolved.torch_device}")
    console.print(f"[bold]Input:[/bold] {input_path}")
    console.print(f"[bold]Output:[/bold] {output_dir / input_path.stem}")

    result = separate_file(input_path, output_dir, options=options)
    console.print("[green]Done.[/green] Wrote stems:")
    for stem in result.stems:
        console.print(f"  - {result.output_dir / (stem + '.wav')}")


@app.command("split")
def split_command(
    input_path: Optional[Path] = typer.Argument(
        None,
        help="Audio file to separate.",
    ),
    output_dir: Path = typer.Option(
        Path("stems"),
        "--output",
        "-o",
        help="Directory where stem folders are written.",
    ),
    model: ModelName = typer.Option(
        DEFAULT_MODEL,
        "--model",
        "-m",
        help="Demucs model to use.",
    ),
    device: DeviceChoice = typer.Option(
        "auto",
        "--device",
        "-d",
        help="Compute device: auto, cpu, or cuda.",
    ),
    two_stems: Optional[str] = typer.Option(
        None,
        "--two-stems",
        help="Keep only one stem plus its complement, e.g. vocals -> vocals + no_vocals.",
    ),
    mode: SeparationMode = typer.Option(
        DEFAULT_SEPARATION_MODE,
        "--mode",
        "-M",
        help="Separation mode: full, vocal_split, or custom.",
    ),
    stems: Optional[str] = typer.Option(
        None,
        "--stems",
        help="Comma-separated stems for custom mode, e.g. vocals,drums.",
    ),
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="YouTube video URL to download and separate.",
    ),
    keep_download: bool = typer.Option(
        False,
        "--keep-download",
        help="Keep the downloaded YouTube audio file after separation.",
    ),
) -> None:
    """Separate one audio file into stems."""
    try:
        if input_path is not None and url is not None:
            raise ValueError("Provide either an input file or --url, not both.")
        if input_path is None and url is None:
            raise ValueError("Provide an input file or --url.")

        selected_stems = _parse_stems_option(stems)
        if mode == "custom" and selected_stems is None:
            raise ValueError("Custom mode requires --stems with at least one stem.")

        resolved_input = input_path
        downloaded_path: Path | None = None
        if url is not None:
            from splitter.sources.youtube import download_audio
            from splitter.temp_cache import release

            console.print("[bold]Downloading audio from YouTube…[/bold]")
            downloaded_path = download_audio(url)
            resolved_input = downloaded_path
            console.print(f"[green]Downloaded:[/green] {downloaded_path}")

        assert resolved_input is not None
        _run_split(resolved_input, output_dir, model, device, mode, selected_stems, two_stems)

        if downloaded_path is not None and not keep_download:
            release(downloaded_path)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("batch")
def batch_command(
    input_dir: Path = typer.Argument(..., help="Directory containing audio files."),
    output_dir: Path = typer.Option(
        Path("stems"),
        "--output",
        "-o",
        help="Directory where stem folders are written.",
    ),
    model: ModelName = typer.Option(
        DEFAULT_MODEL,
        "--model",
        "-m",
        help="Demucs model to use.",
    ),
    device: DeviceChoice = typer.Option(
        "auto",
        "--device",
        "-d",
        help="Compute device: auto, cpu, or cuda.",
    ),
    two_stems: Optional[str] = typer.Option(
        None,
        "--two-stems",
        help="Keep only one stem plus its complement, e.g. vocals -> vocals + no_vocals.",
    ),
    mode: SeparationMode = typer.Option(
        DEFAULT_SEPARATION_MODE,
        "--mode",
        "-M",
        help="Separation mode: full, vocal_split, or custom.",
    ),
    stems: Optional[str] = typer.Option(
        None,
        "--stems",
        help="Comma-separated stems for custom mode, e.g. vocals,drums.",
    ),
) -> None:
    """Separate every supported audio file in a directory."""
    try:
        selected_stems = _parse_stems_option(stems)
        if mode == "custom" and selected_stems is None:
            raise ValueError("Custom mode requires --stems with at least one stem.")
        files = list(iter_audio_files(input_dir))
        resolved = resolve_device(device)
        _print_device_warning(resolved)

        options = SeparationOptions(
            model=model,
            device=device,
            mode=mode,
            selected_stems=selected_stems,
            two_stems=two_stems,
            progress=True,
        )

        console.print(f"[bold]Batch:[/bold] {len(files)} file(s) from {input_dir}")
        results = separate_many(files, output_dir, options=options)
        console.print(f"[green]Done.[/green] Wrote stems for {len(results)} track(s).")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("info")
def info_command() -> None:
    """Show environment details and supported models."""
    resolved = resolve_device("auto")

    table = Table(title=f"Splitter v{__version__}")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("Default model", DEFAULT_MODEL)
    table.add_row("Supported models", ", ".join(SUPPORTED_MODELS))
    table.add_row("CUDA available", "yes" if resolved.cuda_available else "no")
    table.add_row("Selected device (auto)", resolved.torch_device)
    table.add_row("PyTorch version", torch.__version__)
    table.add_row("ffmpeg on PATH", "yes" if ffmpeg_available() else "no")
    console.print(table)

    console.print("\n[bold]Separation modes:[/bold] " + ", ".join(SUPPORTED_SEPARATION_MODES))
    console.print("[bold]Available stems:[/bold] " + ", ".join(FOUR_STEM_OUTPUTS))
    console.print("\n[bold]Two-stem sources:[/bold] " + ", ".join(TWO_STEM_SOURCES))
    console.print(
        "\n[dim]First run downloads model weights (~300 MB for htdemucs, ~1.3 GB for htdemucs_ft).[/dim]"
    )


if __name__ == "__main__":
    app()
