# Changelog

All notable changes to **Audio Splitter** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Release tags on GitHub use the pattern `v{version}` (for example `v0.1.2`). Each push
to `main` with notes under `[Unreleased]` auto-increments the patch version
(`0.1.1` → `0.1.2`) and publishes a new release.

**Workflow:**

1. Add release notes under `## [Unreleased]` while you work.
2. Push to `main`. GitHub Actions increments the patch version, promotes `[Unreleased]`
   into `## [version] - YYYY-MM-DD`, resets `[Unreleased]`, and publishes the release.
3. Download artifacts named `AudioSplitter-{version}-Windows-x64.zip`.

You do **not** need to bump `pyproject.toml` or create version headings manually.

## [Unreleased]
### Added

### Changed

- PyInstaller desktop bundle: replace `collect_all` for torch/torchaudio with minimal custom hooks and exclude unused PyTorch subpackages (testing, distributed, ONNX, etc.) so release zips stay under GitHub's 2 GB asset limit

### Fixed

### Removed

## [0.1.6] - 2026-07-04
### Added

### Changed

- Track maintained Demucs fork ([adefossez/demucs](https://github.com/adefossez/demucs) 4.1.0a3) instead of archived Meta PyPI release 4.0.1; local `load_track()` uses `demucs.audio` APIs removed from the fork CLI module
- Stem save dialog defaults to WAV and only offers audio export formats; non-WAV exports use ffmpeg when available
- Desktop file dialogs use pywebview `FileDialog` constants instead of deprecated `OPEN_DIALOG` / `SAVE_DIALOG`
- Desktop branding: custom logo in the header (title centered, icon left) and as the app/window favicon
- Desktop UI redesigned as a studio-console layout: warm charcoal surfaces, amber accent, two-column workflow (setup left, preview/results right), flat panels, segmented controls, and mixer-style stem color rails
- Desktop audio source UI: Local file and YouTube are toggle tabs that share one input row—the field shows the selected file path or a YouTube URL, and the action button switches between **Select audio file** and **Load from YouTube** (the separate full-width file picker button was removed)
- Release CI installs the Demucs fork with `--no-deps` (after PyTorch), bundles `yt-dlp` for YouTube support in desktop builds, and upgrades `actions/checkout` and `actions/setup-python` to v6 (Node.js 24)

### Fixed

- Desktop app startup crash on Windows when loading the window icon (regenerated a valid multi-resolution `.ico`; `webview.start` now only passes `.ico`, not PNG)

### Removed

## [0.1.5] - 2026-07-04
### Added

### Changed

### Fixed

- Windows EXE startup no longer fails with `Python.Runtime.Loader.Initialize` or missing `System.Windows.Forms` when launched from a downloaded release (pythonnet/clr_loader bundling, .NET Framework runtime, Mark-of-the-Web unblock)

### Removed

## [0.1.4] - 2026-07-04
### Added

### Changed

### Fixed

- Windows EXE startup no longer fails with `Python.Runtime.Loader.Initialize` when launched from a downloaded release (pythonnet/clr_loader bundling, coreclr runtime, Mark-of-the-Web unblock)

### Removed

## [0.1.3] - 2026-07-04
### Added

### Changed

### Fixed

- Packaged desktop app now loads UI assets from the PyInstaller bundle path (`splitter/desktop/ui`) instead of a missing `ui/` folder

### Removed

## [0.1.2] - 2026-07-04
### Added

- YouTube URL input in the desktop app: download audio to a temp cache, preview the full track, then split
- CLI `splitter split --url` for downloading and separating a YouTube video in one command
- Optional `--keep-download` flag to retain the temporary YouTube audio file after CLI separation
- `splitter.sources.youtube` module (yt-dlp + ffmpeg) and temp download cache under `%TEMP%\AudioSplitter\downloads`

### Changed

- Desktop workflow is now load → preview → Split for both local files and YouTube URLs (split no longer starts automatically on file pick)
- Windows release builds bundle CUDA-enabled PyTorch (cu124) so separation uses an NVIDIA GPU when available; falls back to CPU otherwise

### Fixed

- GitHub release workflow: fail fast when version output is empty, validate semver tags, and write `GITHUB_OUTPUT` with UTF-8 so releases are tagged as `v0.1.2` instead of bare `v`

### Removed

## [0.1.1] - 2026-07-04

### Added

- Three separation modes in the desktop app and CLI: **Full** (four stems), **Vocal split** (vocals + instrumental), and **Custom** (user-selected stems)
- Desktop split mode selector with stem checkboxes for custom mode
- CLI flags `--mode` and `--stems` for choosing separation mode

### Changed

- GitHub Releases now use patch-version tags (`v0.1.2`) instead of build-number suffixes; each release auto-increments the patch version and names the zip `AudioSplitter-{version}-Windows-x64.zip`

### Fixed

- GitHub release workflow: replace deprecated Node 20-based release action with `gh` CLI to fix asset upload 307 errors
- GitHub Actions release workflow: fix PowerShell syntax when detecting promoted `CHANGELOG.md` changes

### Removed

## [0.1.0] - 2026-07-04

### Added

- **Desktop application** (`splitter-desktop`) using pywebview with an embedded HTML/CSS/JS UI
- File picker, original and stem audio preview, individual stem saves, zip export, and open-output-folder action
- Automatic `ffmpeg.exe` bundling in release builds with `PATH` setup for compressed audio formats
- **PyInstaller** spec at `build/splitter-desktop.spec` producing `dist/AudioSplitter/AudioSplitter.exe`
- **GitHub Actions** workflow (`.github/workflows/release.yml`) that builds Windows releases on every push to `main`
- Release artifact `AudioSplitter-Windows-x64.zip` tagged as `v{version}-build.{run_number}`
- `validate_file_size()` helper and optional `max_mb` argument on `validate_input_path()`
- `DEFAULT_MAX_FILE_SIZE_MB` constant (50 MB when enforced by a caller)
- Desktop API tests in `tests/test_desktop.py`
- File-size validation tests in `tests/test_cli.py`
- `AGENTS.md` and `CHANGELOG.md` project documentation

### Changed

- `pyproject.toml` description updated to cover CLI and desktop app
- Optional dependency group `[desktop]` added (`pywebview`, `pyinstaller`)
- README rewritten for local CLI + desktop app workflow

### Removed

- Experimental cloud-hosted web UI and remote processing backend (superseded by desktop app)
