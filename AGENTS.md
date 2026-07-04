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
- **Release tags:** `v{version}` (for example `v0.1.2`); CI auto-increments the patch version on each release

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
│   ├── sources/youtube.py         # YouTube download via yt-dlp
│   ├── temp_cache.py              # Temp download cache
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
pip install -e ".[desktop]"       # Desktop app + PyInstaller + yt-dlp
pip install -e ".[youtube]"       # YouTube URL support only (CLI)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124   # GPU builds (matches release)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu   # CPU-only local builds
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
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pyinstaller --noconfirm build/splitter-desktop.spec
# Output: dist/AudioSplitter/AudioSplitter.exe
```

CI release builds use the same CUDA wheel index (`cu124`). Use CPU wheels only when testing a smaller local package.

**Running checks after changes:**

- Run `pytest -m "not slow"` after Python changes.
- Run PyInstaller locally only when touching packaging, desktop entry point, or bundled assets.
- CI bumps `version` in `pyproject.toml` automatically on each release; only bump manually for a new major/minor series.

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

- Long-running download and separation run in background threads (`_run_download`, `_run_separation`).
- UI polls `get_status()`; never block the pywebview main thread on yt-dlp or Demucs work.
- Job statuses: `idle`, `downloading`, `ready`, `queued`, `running`, `done`, `error`.
- Desktop workflow: load source (local or YouTube) → preview → explicit Split.

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
4. Do **not** bump `version` in `pyproject.toml` for routine releases; CI increments the patch version automatically.

**Release workflow:**

1. Ensure `[Unreleased]` contains the notes for the upcoming release.
2. Push to `main`.

**What CI does automatically:**

1. Computes the next patch version from the latest `## [x.y.z]` section in `CHANGELOG.md`.
2. Runs `scripts/sync_changelog.py --prepare-release` to:
   - Create `## [version] - YYYY-MM-DD` from `[Unreleased]`
   - Reset `[Unreleased]` to empty subsections
   - Update `pyproject.toml` and `src/splitter/__init__.py`
   - Commit version files with `[skip ci]` so the release job does not loop
3. Extracts the `## [version]` section into the GitHub Release body.
4. Builds and uploads `AudioSplitter-{version}-Windows-x64.zip` tagged as `v{version}`.

**Local helper:**

```powershell
python scripts/sync_changelog.py --prepare-release
python scripts/sync_changelog.py --extract release-notes.md
```
