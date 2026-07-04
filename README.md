# Splitter

Local CLI for splitting a mixed audio track into **vocals**, **drums**, **bass**, and **other** stems using [Meta Demucs](https://github.com/facebookresearch/demucs) (`htdemucs_ft` by default).

## What you get

| Stem | Contents |
|------|----------|
| `vocals` | Lead and backing vocals |
| `drums` | Drum kit and percussion |
| `bass` | Bass guitar, synth bass, low-end |
| `other` | Everything else (guitars, keys, synths, strings, etc.) |

Open-source models do **not** isolate every instrument into its own file. For guitar and piano as separate stems, Demucs offers an experimental 6-stem model (`htdemucs_6s`) — planned for a future release.

## Requirements

- **Python 3.11+**
- **ffmpeg** on your PATH (needed for MP3, FLAC, M4A, and other compressed formats)
- **~2 GB disk** for Python packages and model weights on first run
- **Optional:** NVIDIA GPU with CUDA for much faster separation

## Install (Windows)

### 1. Install ffmpeg

```powershell
winget install Gyan.FFmpeg
```

Restart your terminal, then verify:

```powershell
ffmpeg -version
```

### 2. Create a virtual environment

```powershell
cd path\to\splitter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3. Install Splitter

```powershell
pip install -e ".[dev]"
```

### 4. Optional — CUDA GPU acceleration

If you have an NVIDIA GPU, install the CUDA build of PyTorch **before** or **after** installing Splitter (re-run if the CPU wheel was picked up):

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

Verify GPU visibility:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

## Usage

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

## Development

```powershell
pip install -e ".[dev]"
pytest -m "not slow"
pytest -m slow
```

## License

Splitter is application code around Demucs. Demucs is MIT-licensed; see the [Demucs repository](https://github.com/facebookresearch/demucs) for model terms and attribution.
