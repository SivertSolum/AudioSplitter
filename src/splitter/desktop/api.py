from __future__ import annotations

import shutil
import sys
import threading
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from splitter.models import FOUR_STEM_OUTPUTS, SUPPORTED_SEPARATION_MODES, SeparationMode
from splitter.separator import SeparationOptions, separate_file, validate_input_path


@dataclass
class JobState:
    job_id: str
    status: str = "idle"
    message: str = ""
    error: str | None = None
    input_path: str | None = None
    output_dir: str | None = None
    stems: list[str] = field(default_factory=list)


class DesktopApi:
    """Python bridge exposed to the embedded web UI via pywebview."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._job = JobState(job_id="")
        self._thread: threading.Thread | None = None

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
            }

    def pick_input_file(self) -> str | None:
        import webview

        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Audio Files (*.mp3;*.wav;*.flac;*.m4a;*.ogg;*.aac;*.wma)",),
        )
        if not result:
            return None
        return str(result[0])

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
            if self._job.status in {"queued", "running"}:
                return {"ok": False, "error": "A separation job is already running."}
            job_id = uuid.uuid4().hex
            self._job = JobState(
                job_id=job_id,
                status="queued",
                message="Queued for separation…",
                input_path=str(path),
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
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stem_path, target)
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

    def pick_save_file(self, suggested_name: str) -> str | None:
        import webview

        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=suggested_name,
        )
        if not result:
            return None
        return str(result)

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
