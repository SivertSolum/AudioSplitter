from __future__ import annotations

import shutil
import sys
import threading
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from splitter.models import FOUR_STEM_OUTPUTS, SUPPORTED_SEPARATION_MODES, SeparationMode
from splitter.audio_io import export_audio_file
from splitter.separator import SeparationOptions, separate_file, validate_input_path
from splitter.temp_cache import release as release_temp_file

STEM_SAVE_FILE_TYPES = (
    "WAV Audio (*.wav)",
    "FLAC Audio (*.flac)",
    "MP3 Audio (*.mp3)",
    "M4A Audio (*.m4a)",
    "OGG Audio (*.ogg)",
    "AAC Audio (*.aac)",
    "WMA Audio (*.wma)",
)

ZIP_SAVE_FILE_TYPES = ("ZIP Archive (*.zip)",)

SourceType = Literal["local", "youtube"]


@dataclass
class JobState:
    job_id: str
    status: str = "idle"
    message: str = ""
    error: str | None = None
    input_path: str | None = None
    output_dir: str | None = None
    stems: list[str] = field(default_factory=list)
    source_type: SourceType | None = None
    display_name: str | None = None
    is_temp_input: bool = False


class DesktopApi:
    """Python bridge exposed to the embedded web UI via pywebview."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._job = JobState(job_id="")
        self._thread: threading.Thread | None = None
        self._loaded_input_path: Path | None = None
        self._loaded_display_name: str | None = None
        self._loaded_source_type: SourceType | None = None
        self._loaded_is_temp: bool = False

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "jobId": self._job.job_id,
                "status": self._job.status,
                "message": self._job.message,
                "error": self._job.error,
                "inputPath": self._job.input_path,
                "outputDir": self._job.output_dir,
                "stems": list(self._job.stems),
                "sourceType": self._job.source_type,
                "displayName": self._job.display_name,
            }

    def pick_input_file(self) -> dict[str, Any]:
        import webview

        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("Audio Files (*.mp3;*.wav;*.flac;*.m4a;*.ogg;*.aac;*.wma)",),
        )
        if not result:
            return {"ok": False}
        path = Path(result[0])
        try:
            validate_input_path(path)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            return {"ok": False, "error": str(exc)}

        self.clear_loaded_input()
        self._set_loaded_input(path, display_name=str(path), source_type="local", is_temp=False)
        return {
            "ok": True,
            "path": str(path),
            "displayName": str(path),
            "uri": path.resolve().as_uri(),
        }

    def download_youtube(self, url: str) -> dict[str, Any]:
        with self._lock:
            if self._job.status in {"downloading", "queued", "running"}:
                return {"ok": False, "error": "A job is already in progress."}

        try:
            from splitter.sources.youtube import validate_youtube_url

            cleaned_url = validate_youtube_url(url)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        self.clear_loaded_input()
        job_id = uuid.uuid4().hex
        with self._lock:
            self._job = JobState(
                job_id=job_id,
                status="downloading",
                message="Downloading audio from YouTube…",
                source_type="youtube",
                display_name=cleaned_url,
            )

        self._thread = threading.Thread(
            target=self._run_download,
            args=(job_id, cleaned_url),
            daemon=True,
        )
        self._thread.start()
        return {"ok": True, "jobId": job_id}

    def get_input_uri(self) -> str | None:
        with self._lock:
            if self._loaded_input_path is None:
                return None
            path = self._loaded_input_path
        if not path.exists():
            return None
        return path.resolve().as_uri()

    def clear_loaded_input(self) -> None:
        with self._lock:
            path = self._loaded_input_path
            is_temp = self._loaded_is_temp
            self._loaded_input_path = None
            self._loaded_display_name = None
            self._loaded_source_type = None
            self._loaded_is_temp = False
            if self._job.status == "ready":
                self._job = JobState(job_id="")

        if path is not None and is_temp:
            release_temp_file(path)

    def get_available_stems(self) -> list[str]:
        return list(FOUR_STEM_OUTPUTS)

    def start_separation(
        self,
        input_path: str,
        mode: str = "full",
        selected_stems: list[str] | None = None,
    ) -> dict[str, Any]:
        path = Path(input_path)
        try:
            validate_input_path(path)
            separation_mode = self._validate_separation_mode(mode)
            stems = self._validate_selected_stems(separation_mode, selected_stems)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            return {"ok": False, "error": str(exc)}

        with self._lock:
            if self._job.status in {"downloading", "queued", "running"}:
                return {"ok": False, "error": "A separation job is already running."}
            if self._loaded_input_path is None or self._loaded_input_path != path:
                return {"ok": False, "error": "Load an audio source before splitting."}
            if self._job.status != "ready":
                return {"ok": False, "error": "Audio is not ready to split."}

            job_id = uuid.uuid4().hex
            self._job = JobState(
                job_id=job_id,
                status="queued",
                message="Queued for separation…",
                input_path=str(path),
                source_type=self._loaded_source_type,
                display_name=self._loaded_display_name,
                is_temp_input=self._loaded_is_temp,
            )

        self._thread = threading.Thread(
            target=self._run_separation,
            args=(job_id, path, separation_mode, stems),
            daemon=True,
        )
        self._thread.start()
        return {"ok": True, "jobId": job_id}

    def get_stem_uri(self, stem_name: str) -> str | None:
        with self._lock:
            if self._job.status != "done" or not self._job.output_dir:
                return None
            stem_path = Path(self._job.output_dir) / f"{stem_name}.wav"
        if not stem_path.exists():
            return None
        return stem_path.resolve().as_uri()

    def save_stem_copy(self, stem_name: str, destination: str) -> dict[str, Any]:
        with self._lock:
            if self._job.status != "done" or not self._job.output_dir:
                return {"ok": False, "error": "No completed stems are available."}
            stem_path = Path(self._job.output_dir) / f"{stem_name}.wav"
        if not stem_path.exists():
            return {"ok": False, "error": f"Stem '{stem_name}' was not found."}
        target = Path(destination)
        try:
            export_audio_file(stem_path, target)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(target)}

    def save_all_stems_zip(self, destination: str) -> dict[str, Any]:
        with self._lock:
            if self._job.status != "done" or not self._job.output_dir:
                return {"ok": False, "error": "No completed stems are available."}
            output_dir = Path(self._job.output_dir)
            stems = list(self._job.stems)
            input_path = Path(self._job.input_path or "stems")

        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for stem in stems:
                stem_path = output_dir / f"{stem}.wav"
                if stem_path.exists():
                    archive.write(stem_path, arcname=f"{stem}.wav")
        return {"ok": True, "path": str(target)}

    def pick_save_file(self, suggested_name: str, kind: str = "stem") -> str | None:
        import webview

        if kind == "zip":
            file_types = ZIP_SAVE_FILE_TYPES
        elif kind == "stem":
            file_types = STEM_SAVE_FILE_TYPES
        else:
            raise ValueError(f"Unsupported save dialog kind: {kind}")

        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=suggested_name,
            file_types=file_types,
        )
        if not result:
            return None
        return str(result[0])

    def open_output_folder(self) -> dict[str, Any]:
        import os
        import subprocess

        with self._lock:
            folder = self._job.output_dir
        if not folder:
            return {"ok": False, "error": "No output folder is available yet."}
        path = Path(folder)
        if not path.exists():
            return {"ok": False, "error": "Output folder does not exist."}
        if os.name == "nt":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return {"ok": True}

    def _set_loaded_input(
        self,
        path: Path,
        *,
        display_name: str,
        source_type: SourceType,
        is_temp: bool,
        job_id: str | None = None,
    ) -> None:
        with self._lock:
            self._loaded_input_path = path
            self._loaded_display_name = display_name
            self._loaded_source_type = source_type
            self._loaded_is_temp = is_temp
            if job_id is not None and self._job.job_id == job_id:
                self._job.status = "ready"
                self._job.message = "Preview the track, then click Split when ready."
                self._job.input_path = str(path)
                self._job.source_type = source_type
                self._job.display_name = display_name
                self._job.is_temp_input = is_temp
                self._job.error = None
            else:
                self._job = JobState(
                    job_id=job_id or uuid.uuid4().hex,
                    status="ready",
                    message="Preview the track, then click Split when ready.",
                    input_path=str(path),
                    source_type=source_type,
                    display_name=display_name,
                    is_temp_input=is_temp,
                )

    def _validate_separation_mode(self, mode: str) -> SeparationMode:
        if mode not in SUPPORTED_SEPARATION_MODES:
            supported = ", ".join(SUPPORTED_SEPARATION_MODES)
            raise ValueError(f"Invalid separation mode '{mode}'. Choose one of: {supported}")
        return mode  # type: ignore[return-value]

    def _validate_selected_stems(
        self,
        mode: SeparationMode,
        selected_stems: list[str] | None,
    ) -> tuple[str, ...] | None:
        if mode != "custom":
            return None
        if not selected_stems:
            raise ValueError("Custom mode requires at least one stem to be selected.")
        invalid = [stem for stem in selected_stems if stem not in FOUR_STEM_OUTPUTS]
        if invalid:
            supported = ", ".join(FOUR_STEM_OUTPUTS)
            raise ValueError(
                f"Invalid stem(s): {', '.join(invalid)}. Choose from: {supported}"
            )
        return tuple(selected_stems)

    def _run_download(self, job_id: str, url: str) -> None:
        try:
            from splitter.sources.youtube import download_audio, fetch_metadata

            metadata = fetch_metadata(url)
            self._set_job(
                job_id,
                message=f"Downloading “{metadata.title}” from YouTube…",
                display_name=metadata.title,
            )
            path = download_audio(url)
            self._set_loaded_input(
                path,
                display_name=metadata.title,
                source_type="youtube",
                is_temp=True,
                job_id=job_id,
            )
        except Exception as exc:  # noqa: BLE001 - show failures in UI
            self._set_job(
                job_id,
                status="error",
                message="YouTube download failed.",
                error=str(exc),
            )

    def _run_separation(
        self,
        job_id: str,
        input_path: Path,
        mode: SeparationMode,
        selected_stems: tuple[str, ...] | None,
    ) -> None:
        self._set_job(
            job_id,
            status="running",
            message="Separating stems with Demucs…",
            error=None,
        )
        is_temp_input = False
        with self._lock:
            is_temp_input = self._job.is_temp_input
        try:
            result = separate_file(
                input_path,
                self.output_root,
                options=SeparationOptions(
                    mode=mode,
                    selected_stems=selected_stems,
                    progress=False,
                ),
            )
            self._set_job(
                job_id,
                status="done",
                message="Separation complete.",
                output_dir=str(result.output_dir),
                stems=list(result.stems),
                error=None,
            )
            if is_temp_input:
                release_temp_file(input_path)
                with self._lock:
                    if self._loaded_input_path == input_path:
                        self._loaded_input_path = None
                        self._loaded_is_temp = False
        except Exception as exc:  # noqa: BLE001 - show failures in UI
            self._set_job(
                job_id,
                status="error",
                message="Separation failed.",
                error=str(exc),
            )

    def _set_job(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            if self._job.job_id != job_id:
                return
            for key, value in fields.items():
                setattr(self._job, key, value)
