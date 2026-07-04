# Changelog

All notable changes to **Audio Splitter** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Release tags on GitHub use the pattern `v{version}-build.{number}` (for example
`v0.1.0-build.42`). The `{version}` segment matches `project.version` in
`pyproject.toml`.

**Workflow:**

1. Add release notes under `## [Unreleased]` while you work.
2. Bump `version` in `pyproject.toml` when you are ready for a new release series.
3. Push to `main`. GitHub Actions promotes `[Unreleased]` into `## [version] - YYYY-MM-DD`
   automatically (if that version section does not exist yet), then publishes the matching
   section as the GitHub Release description.

You do **not** need to create the version heading or date manually.

## [Unreleased]

### Added

### Changed

### Fixed

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
