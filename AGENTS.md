---
name: audio-splitter
description: Expert Python developer for the Audio Splitter CLI and desktop Demucs stem-separation app.
---

# Audio Splitter — agent guide

You are an expert Python developer working on **Audio Splitter**, a local tool that splits mixed audio into **vocals**, **drums**, **bass**, and **other** stems using [Meta Demucs](https://github.com/facebookresearch/demucs).

## Persona

- Prefer small, focused changes that reuse the existing `separate_file()` pipeline rather than duplicating Demucs logic.
- Treat separation as **local-only**: no cloud uploads, no remote APIs, no hosted backends.
- Keep the CLI stable; extend the desktop app or core library when adding user-facing features.
- Match existing patterns: Typer for CLI, dataclasses for options/results, pytest with mocks for unit tests, `@pytest.mark.slow` for real inference.

## Project knowledge

- **Tech stack:** Python 3.11+, Demucs, PyTorch, Typer, Rich, pywebview (desktop), PyInstaller (packaging)
- **Entry points:** `splitter` (CLI), `splitter-desktop` (GUI)
- **Default model:** `htdemucs_ft` (four stems)
- **Release tags:** `v{version}-build.{number}` where `{version}` comes from `pyproject.toml`

**File structure:**

```
audio-splitter/
├── pyproject.toml                 # Version source of truth
├── CHANGELOG.md                   # Release notes source of truth for GitHub Releases
├── AGENTS.md                      # This file
├── README.md                      # User-facing documentation
├── src/splitter/
│   ├── cli.py                     # Typer commands: split, batch, info
│   ├── separator.py               # Core pipeline: separate_file(), validate_input_path()
│   ├── models.py                  # Model names, resolve_device()
│   ├── audio_io.py                # WAV writer
│   └── desktop/
│       ├── app.py                 # pywebview launcher
│       ├── api.py                 # JS ↔ Python bridge (DesktopApi)
│       └── ui/                    # Embedded index.html, app.js, styles.css
├── build/splitter-desktop.spec    # PyInstaller onedir spec
├── .github/workflows/release.yml  # Windows build + GitHub Release on push to main
└── tests/
    ├── test_cli.py
    └── test_desktop.py
```

**Supported input formats:** `.mp3`, `.wav`, `.flac`, `.m4a`, `.ogg`, `.aac`, `.wma` (non-WAV requires ffmpeg on `PATH`).

**Output:** 16-bit PCM WAV stems under `{output_dir}/{track_stem}/`.

## Available tools

**Install:**

```powershell
pip install -e ".[dev]"           # CLI + tests
pip install -e ".[desktop]"       # Desktop app + PyInstaller
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu   # CPU wheels for local builds
```

**CLI:**

```powershell
splitter split song.mp3
splitter batch .\album\
splitter info
```

**Desktop (development):**

```powershell
splitter-desktop
```

**Tests:**

```powershell
pytest -m "not slow"
pytest -m slow                    # Real Demucs inference — slow, optional
```

**Package executable locally:**

```powershell
pyinstaller --noconfirm build/splitter-desktop.spec
# Output: dist/AudioSplitter/AudioSplitter.exe
```

**Running checks after changes:**

- Run `pytest -m "not slow"` after Python changes.
- Run PyInstaller locally only when touching packaging, desktop entry point, or bundled assets.
- Bump `version` in `pyproject.toml` when preparing a user-visible release (not required for every CI build tag).

## Standards

**Naming conventions:**

- Package/module: `splitter`, snake_case files and functions
- CLI command: `splitter`; desktop command: `splitter-desktop`
- Desktop UI assets live under `src/splitter/desktop/ui/`

**Core pattern — call the pipeline, don't reimplement Demucs:**

```python
from pathlib import Path
from splitter.separator import SeparationOptions, separate_file

result = separate_file(
    Path("song.mp3"),
    Path("stems"),
    options=SeparationOptions(model="htdemucs_ft", device="auto", progress=False),
)
# result.output_dir, result.stems
```

**Desktop API pattern:**

- Long-running separation runs in a background thread (`DesktopApi._run_separation`).
- UI polls `get_status()`; never block the pywebview main thread on Demucs inference.

**Common patterns:**

- Validate inputs with `validate_input_path()` before separation.
- Pass `max_mb=` only when a caller needs an upload/size guard (desktop or future APIs); CLI defaults leave size unchecked.
- Packaged app output: `%USERPROFILE%\Music\AudioSplitter\stems`; dev mode: `./stems`.

**Boundaries:**

- Do **not** add cloud hosting, serverless backends, or browser-only separation unless explicitly requested.
- Do **not** pin PyTorch in `pyproject.toml` — document CPU/CUDA install separately (matches README).
- Avoid bundling Demucs model weights in the executable; they download on first run (~1.3 GB for `htdemucs_ft`).
- Keep changes scoped: don't refactor unrelated CLI code when fixing desktop UI issues.

## Changelog and releases

**`CHANGELOG.md` is the canonical source for GitHub Release descriptions.**

**Whenever you change this project, update `CHANGELOG.md` in the same task.** Do not leave
changelog updates for the user. Add bullets under `## [Unreleased]` as part of every PR-sized
change set — features, fixes, refactors with user impact, docs, CI, packaging, and tests that
reflect new behavior. Skip changelog entries only for trivial internal edits with no user-visible
effect (for example typo fixes in comments).

When you make user-visible changes:

1. Add entries under `## [Unreleased]` only — in `Added`, `Changed`, `Fixed`, or `Removed`.
2. Use concise, user-facing bullet points (not commit hashes).
3. Do **not** create `## [x.y.z]` sections manually; CI writes them for you.

**When you are ready for a new release version:**

1. Bump `version` in `pyproject.toml` (for example `0.1.0` → `0.2.0`).
2. Ensure `[Unreleased]` contains the notes for that release.
3. Push to `main`.

**What CI does automatically:**

1. Reads `project.version` from `pyproject.toml`.
2. If `## [version]` is missing, runs `scripts/sync_changelog.py --promote` to:
   - Create `## [version] - YYYY-MM-DD` from `[Unreleased]`
   - Reset `[Unreleased]` to empty subsections
   - Commit `CHANGELOG.md` with `[skip ci]` so the release job does not loop
3. Extracts the `## [version]` section into the GitHub Release body.
4. Builds and uploads `AudioSplitter-Windows-x64.zip` tagged as `v{version}-build.{run_number}`.

**Build-only releases** (same `pyproject.toml` version, new `-build.N` tag) reuse the existing
`## [version]` section for release notes. Keep accumulating the *next* release under
`[Unreleased]` without bumping the version until you are ready.

**Local helper:**

```powershell
python scripts/sync_changelog.py --promote
python scripts/sync_changelog.py --extract release-notes.md
```
