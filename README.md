# Splitter

CLI and desktop app for splitting a mixed audio track into **vocals**, **drums**, **bass**, and **other** stems using [Meta Demucs](https://github.com/facebookresearch/demucs) (`htdemucs_ft` by default).

Everything runs locally on your machine. No cloud hosting or uploads are required.

## What you get

| Stem | Contents |
|------|----------|
| `vocals` | Lead and backing vocals |
| `drums` | Drum kit and percussion |
| `bass` | Bass guitar, synth bass, low-end |
| `other` | Everything else (guitars, keys, synths, strings, etc.) |

Open-source models do **not** isolate every instrument into its own file. For guitar and piano as separate stems, Demucs offers an experimental 6-stem model (`htdemucs_6s`) — planned for a future release.

## Project layout

```
audio-splitter/
├── src/splitter/              # Core Python package
│   ├── cli.py                 # Typer CLI (`splitter` command)
│   ├── separator.py           # Demucs separation pipeline
│   ├── models.py              # Model names and device resolution
│   ├── audio_io.py            # WAV output writer
│   └── desktop/               # Desktop GUI (pywebview)
│       ├── app.py             # Window launcher
│       ├── api.py             # Python ↔ UI bridge
│       └── ui/                # Embedded HTML/CSS/JS UI
├── build/
│   └── splitter-desktop.spec  # PyInstaller build spec
├── .github/workflows/
│   └── release.yml            # Windows release build on push to main
└── tests/
```

## Requirements

- **Python 3.11+** (CLI and development)
- **ffmpeg** on your PATH for MP3, FLAC, M4A, and other compressed formats (included in GitHub release builds)
- **~2 GB disk** for Python packages and model weights on first run
- **Optional:** NVIDIA GPU with CUDA for much faster separation

---

## CLI

### Install (Windows)

#### 1. Install ffmpeg

```powershell
winget install Gyan.FFmpeg
```

Restart your terminal, then verify:

```powershell
ffmpeg -version
```

#### 2. Create a virtual environment

```powershell
cd path\to\audio-splitter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

#### 3. Optional — CUDA GPU acceleration

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.cuda.is_available())"
```

### CLI usage

```powershell
# Separate one track (writes to ./stems/{track_name}/)
splitter split song.mp3

# Custom output folder
splitter split song.mp3 -o .\output

# Faster preview model (lower quality)
splitter split song.mp3 --model htdemucs

# Force CPU or CUDA
splitter split song.mp3 --device cpu
splitter split song.mp3 --device cuda

# Karaoke / instrumental mode
splitter split song.mp3 --two-stems vocals

# Batch-process a folder
splitter batch .\album\ -o .\stems

# Environment and model info
splitter info
```

### Output layout

```
stems/
└── song_name/
    ├── vocals.wav
    ├── drums.wav
    ├── bass.wav
    └── other.wav
```

With `--two-stems vocals`:

```
stems/
└── song_name/
    ├── vocals.wav
    └── no_vocals.wav
```

---

## Desktop app

The desktop app provides a graphical interface for the same separation pipeline used by the CLI.

### Run from source

```powershell
pip install -e ".[desktop]"
splitter-desktop
```

### Features

- Select an audio file from a native file picker
- Preview the original track and separated stems
- Save individual stems or all stems in one zip
- Open the output folder when processing completes

**Output locations**

| Mode | Stems folder |
|------|----------------|
| Packaged `.exe` | `%USERPROFILE%\Music\AudioSplitter\stems` |
| Development | `./stems` (current working directory) |

### Download a release build

Every push to `main` creates a tagged GitHub Release with a Windows build:

1. Open the repository **Releases** page on GitHub
2. Download `AudioSplitter-Windows-x64.zip`
3. Extract the folder and run `AudioSplitter.exe`

Release tags look like `v0.1.0-build.42`. To start a new release series, bump `version` in
`pyproject.toml` and add notes under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md). CI
creates the version section and date automatically on the next push to `main`.

The release bundle includes `ffmpeg.exe` for MP3/FLAC/M4A support. Demucs model weights still download on first run (~1.3 GB).

Release tags follow the pattern `v{version}-build.{number}` (for example `v0.1.0-build.42`).

### Build the executable locally

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[desktop]"
pyinstaller --noconfirm build/splitter-desktop.spec
```

The built app is placed in `dist/AudioSplitter/`.

---

## Models

| Model | Stems | Quality | Speed | Notes |
|-------|-------|---------|-------|-------|
| `htdemucs_ft` | 4 | Best | Slower | **Default.** Fine-tuned bag (~1.3 GB download) |
| `htdemucs` | 4 | Good | Faster | Single-file model (~300 MB) |

First run downloads weights into the Demucs cache (typically `%USERPROFILE%\.cache\torch\hub\checkpoints\`).

## Performance

Rough guide for a 3-minute song:

| Hardware | Model | Time |
|----------|-------|------|
| NVIDIA GPU (CUDA) | `htdemucs_ft` | ~1–2 min |
| CPU only | `htdemucs_ft` | ~5–15 min |
| CPU only | `htdemucs` | ~3–8 min |

CPU separation is supported but slow. The CLI warns when running on CPU.

---

## Development

```powershell
pip install -e ".[dev]"
pytest -m "not slow"
pytest -m slow
```

Agent and changelog conventions for contributors and AI assistants are in [AGENTS.md](AGENTS.md).

Optional dependency groups:

| Group | Purpose |
|-------|---------|
| `dev` | pytest |
| `desktop` | pywebview, PyInstaller |

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

## License

Splitter is application code around Demucs. Demucs is MIT-licensed; see the [Demucs repository](https://github.com/facebookresearch/demucs) for model terms and attribution.
