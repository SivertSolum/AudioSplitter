from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from splitter.separator import DEFAULT_MAX_FILE_SIZE_MB, validate_input_path
from splitter.temp_cache import clear_previous_downloads, register_active, target_path

YOUTUBE_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+",
    re.IGNORECASE,
)
DEFAULT_AUDIO_FORMAT = "mp3"
# Rough upper bound for 320 kbps MP3 before download (bytes per second).
_ESTIMATED_MP3_BYTES_PER_SECOND = 40_000


@dataclass(frozen=True)
class VideoMetadata:
    video_id: str
    title: str
    duration: int | None


def _require_yt_dlp():
    try:
        import yt_dlp  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is required for YouTube downloads. "
            'Install with: pip install -e ".[youtube]"'
        ) from exc


def validate_youtube_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("YouTube URL cannot be empty.")
    if not YOUTUBE_URL_PATTERN.match(cleaned):
        raise ValueError("URL must be a valid YouTube video link.")
    return cleaned


def _ffmpeg_location() -> str | None:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        bundled = exe_dir / "ffmpeg.exe"
        if bundled.exists():
            return str(exe_dir)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return str(Path(ffmpeg).parent)
    return None


def _base_ydl_options() -> dict:
    options: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    ffmpeg_location = _ffmpeg_location()
    if ffmpeg_location:
        options["ffmpeg_location"] = ffmpeg_location
    return options


def estimate_download_size_mb(duration_seconds: int | None) -> float | None:
    if duration_seconds is None or duration_seconds <= 0:
        return None
    return (duration_seconds * _ESTIMATED_MP3_BYTES_PER_SECOND) / (1024 * 1024)


def check_download_size(duration_seconds: int | None, *, max_mb: int = DEFAULT_MAX_FILE_SIZE_MB) -> None:
    estimated = estimate_download_size_mb(duration_seconds)
    if estimated is None:
        return
    if estimated > max_mb:
        raise ValueError(
            f"Estimated download size ({estimated:.1f} MB) exceeds the {max_mb} MB limit. "
            "Choose a shorter video."
        )


def fetch_metadata(url: str) -> VideoMetadata:
    _require_yt_dlp()
    import yt_dlp

    cleaned = validate_youtube_url(url)
    options = {
        **_base_ydl_options(),
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(cleaned, download=False)

    video_id = info.get("id")
    title = info.get("title") or "YouTube audio"
    duration = info.get("duration")
    if not video_id:
        raise ValueError("Could not read video metadata from YouTube.")

    check_download_size(duration)
    return VideoMetadata(video_id=video_id, title=title, duration=duration)


def download_audio(
    url: str,
    dest_dir: Path | None = None,
    *,
    max_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
) -> Path:
    _require_yt_dlp()
    import yt_dlp

    metadata = fetch_metadata(url)
    output_path = target_path(metadata.video_id, f".{DEFAULT_AUDIO_FORMAT}")
    if dest_dir is not None:
        output_path = dest_dir / output_path.name

    if output_path.exists():
        try:
            validate_input_path(output_path, max_mb=max_mb)
            register_active(output_path)
            return output_path
        except (ValueError, RuntimeError):
            output_path.unlink(missing_ok=True)

    clear_previous_downloads()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_path.with_suffix("")) + ".%(ext)s"

    options = {
        **_base_ydl_options(),
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": DEFAULT_AUDIO_FORMAT,
                "preferredquality": "0",
            }
        ],
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    if not output_path.exists():
        candidates = sorted(output_path.parent.glob(f"{metadata.video_id}.*"))
        if not candidates:
            raise RuntimeError("YouTube download finished but no audio file was created.")
        output_path = candidates[0]

    validate_input_path(output_path, max_mb=max_mb)
    register_active(output_path)
    return output_path
