# Splitter

CLI and desktop app for splitting a mixed audio track into **vocals**, **drums**, **bass**, and **other** stems using [Demucs](https://github.com/adefossez/demucs) (`htdemucs_ft` by default).

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
│   ├── sources/youtube.py     # YouTube audio download (yt-dlp)
│   ├── temp_cache.py          # Temp download cache for YouTube input
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
- **yt-dlp** for YouTube input (`pip install -e ".[youtube]"` or included in `.[desktop]`)
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

Install **PyTorch before Demucs** — the maintained Demucs fork pins an older `torchaudio` range, so AudioSplitter installs it with `--no-deps` after PyTorch is in place.

```powershell
cd path\to\audio-splitter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install dora-search einops "julius>=0.2.3" "lameenc>=1.2" openunmix pyyaml tqdm
pip install --no-deps "demucs @ git+https://github.com/adefossez/demucs@b9ab48cad45976ba42b2ff17b229c071f0df9390"
pip install -e ".[dev]" --no-deps
pip install typer rich pytest
```

For CPU-only PyTorch, use `--index-url https://download.pytorch.org/whl/cpu` instead of `cu124`.

#### 3. Verify CUDA (optional)

```powershell
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

# Separate audio from a YouTube URL (downloads to a temp file first)
splitter split --url "https://www.youtube.com/watch?v=..." -o .\stems

# Keep the downloaded file after separation
splitter split --url "https://www.youtube.com/watch?v=..." --keep-download

# Environment and model info
splitter info
```

YouTube downloads are limited to roughly **50 MB** estimated size (about 20 minutes at high quality). Use local files for longer sources.

> **Note:** Downloading audio from YouTube may violate YouTube's Terms of Service. You are responsible for ensuring you have the right to use any content you process.

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

- Load audio from a **local file** or a **YouTube URL**
- Preview the full track before splitting
- Click **Split** when ready (Demucs separation)
- Preview separated stems after processing
- Save individual stems or all stems in one zip
- Open the output folder when processing completes

YouTube audio is stored temporarily under `%TEMP%\AudioSplitter\downloads\` and removed after a successful split.

**Output locations**

| Mode | Stems folder |
|------|----------------|
| Packaged `.exe` | `%USERPROFILE%\Music\AudioSplitter\stems` |
| Development | `./stems` (current working directory) |

### Download a release build

Every push to `main` creates a tagged GitHub Release with a Windows build:

1. Open the repository **Releases** page on GitHub
2. Download `AudioSplitter-{version}-Windows-x64.zip` (for example `AudioSplitter-0.1.2-Windows-x64.zip`)
3. Extract the folder and run `AudioSplitter.exe`

Add notes under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md) before pushing to `main`. CI
auto-increments the patch version (`0.1.1` → `0.1.2`), creates the changelog section, and
publishes release tag `v0.1.2`.

The release bundle includes `ffmpeg.exe` for MP3/FLAC/M4A support and **CUDA-enabled PyTorch** (cu124) for NVIDIA GPU acceleration. Demucs uses your GPU automatically when drivers are installed; otherwise it falls back to CPU. Model weights still download on first run (~1.3 GB).

The CUDA runtime makes the zip larger than a CPU-only build. An NVIDIA GPU with up-to-date drivers is recommended for fast separation.

**Windows startup errors (`Python.Runtime.Loader.Initialize` or `System.Windows.Forms`)** — If the app fails immediately after downloading from GitHub, Windows may have marked the zip as untrusted. Right-click the zip → **Properties** → check **Unblock** → **OK**, then extract again. Newer releases also clear this automatically on first launch. The desktop UI also requires **.NET Framework 4.7.2+** (included on Windows 10/11 by default).

### Build the executable locally

Match the release workflow with CUDA PyTorch (recommended if you have an NVIDIA GPU):

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install dora-search einops "julius>=0.2.3" "lameenc>=1.2" openunmix pyyaml tqdm pywebview pyinstaller
pip install --no-deps "demucs @ git+https://github.com/adefossez/demucs@b9ab48cad45976ba42b2ff17b229c071f0df9390"
pip install -e ".[desktop]" --no-deps
pip install typer rich
pyinstaller --noconfirm build/splitter-desktop.spec
```

For a smaller local build without GPU support:

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install dora-search einops "julius>=0.2.3" "lameenc>=1.2" openunmix pyyaml tqdm pywebview pyinstaller
pip install --no-deps "demucs @ git+https://github.com/adefossez/demucs@b9ab48cad45976ba42b2ff17b229c071f0df9390"
pip install -e ".[desktop]" --no-deps
pip install typer rich
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
| `youtube` | yt-dlp for YouTube URL input |
| `desktop` | pywebview, PyInstaller, yt-dlp |

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

## License

Splitter is application code around Demucs. Demucs is MIT-licensed; see the [Demucs repository](https://github.com/adefossez/demucs) for model terms and attribution. The original Meta repository is [archived](https://github.com/facebookresearch/demucs).
