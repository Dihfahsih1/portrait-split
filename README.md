<div align="center">

<br/>

```
██████╗  ██████╗ ██████╗ ████████╗██████╗  █████╗ ██╗████████╗    ███████╗██████╗ ██╗     ██╗████████╗
██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██║╚══██╔══╝    ██╔════╝██╔══██╗██║     ██║╚══██╔══╝
██████╔╝██║   ██║██████╔╝   ██║   ██████╔╝███████║██║   ██║       ███████╗██████╔╝██║     ██║   ██║   
██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══██╗██╔══██║██║   ██║       ╚════██║██╔═══╝ ██║     ██║   ██║   
██║     ╚██████╔╝██║  ██║   ██║   ██║  ██║██║  ██║██║   ██║       ███████║██║     ███████╗██║   ██║   
╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝       ╚══════╝╚═╝     ╚══════╝╚═╝   ╚═╝   
```

### 🎬 Face-tracked HD portrait video. Like TikTok Smart Cut — but free, open-source, and yours.

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-6C63FF.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%20Linux-orange?style=for-the-badge&logo=ubuntu)](https://ubuntu.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Powered-007808?style=for-the-badge&logo=ffmpeg)](https://ffmpeg.org)

<br/>

**[Install Now](#-install-one-command)** · **[See How It Works](#-how-it-works)** · **[CLI Reference](#%EF%B8%8F-command-line)**

<br/>

---

</div>

## 🤔 What Is This?

You recorded a 3-hour conference, seminar, or sermon in landscape (16:9). Now you want to put it on **TikTok, Instagram Reels, or YouTube Shorts** — but that means portrait (9:16), and your speaker can't be half off-screen.

**Portrait Split does all of this automatically:**

| Step | What happens |
|---|---|
| 🎯 **Face tracking** | OpenCV detects the speaker's face every few frames |
| 📐 **Smart reframe** | Crops a 9:16 window that follows the face with smooth motion |
| 📱 **Full HD output** | Outputs 1080×1920 — not a tiny crop, full HD portrait |
| ✂️ **Auto-split** | Cuts into segments of any length (default 3 min 20 s) |
| ⚡ **Parallel processing** | Multiple segments encode at the same time |
| 🔊 **Perfect audio sync** | Two-step seek guarantees lips and words always match |
| 🖥️ **Desktop GUI** | Clean dark UI — no terminal knowledge needed |

This is what TikTok's "Smart Cut" feature does — except Portrait Split runs locally on your machine, costs nothing, and works on any video.

---

## 📥 Install — One Command

Open a terminal (`Ctrl+Alt+T`) and paste this:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/autopro-ug/portrait-split/main/install.sh)
```

That's it. The installer handles everything:
- ✅ Installs `ffmpeg` and Python dependencies
- ✅ Creates an isolated environment (won't break your system Python)
- ✅ Adds **Portrait Split** to your Ubuntu app menu
- ✅ Creates `portrait-split` terminal command

**After install, search "Portrait Split" in your app menu and open it.**

> Requires Ubuntu 20.04 or later. Takes about 2–3 minutes on first run.

---

## 🖥️ The App

<div align="center">

*Dark, modern UI with live progress log, per-segment stats, and full settings control.*

</div>

### Using the GUI

1. **Click the input zone** → pick your MP4 file
2. **Click the output zone** → pick where to save
3. **Adjust settings** if needed (defaults work great)
4. **Hit Start** → watch it process in the log tab

### Settings explained

| Setting | Default | What it does |
|---|---|---|
| **Segment length** | `200s` | How long each output clip is (3 min 20 s) |
| **Parallel segments** | `4` | How many clips encode at once — more = faster, uses more CPU |
| **CRF quality** | `18` | Video quality. 0 = lossless, 18 = near-lossless, 28 = good for web |
| **Encoding preset** | `fast` | Speed vs file size tradeoff |
| **Tracking speed** | `0.3` | How quickly camera follows face. 0.1 = cinematic, 1.0 = instant snap |
| **Max jump** | `400px` | Ignores faces far from the main speaker (e.g. interpreter off to side) |
| **Max drift** | `6px/frame` | Caps pan speed — prevents dizzying camera snaps |

---

## 🔧 How It Works

```
Your landscape video  (1920×1080, 16:9)
          │
          ▼
  ┌───────────────────────────────────────────────────┐
  │  OpenCV Haar Cascade Face Detector                │
  │  • Runs every 5 frames on a ¼-resolution thumb    │
  │  • ~16× fewer pixels = dramatically faster        │
  │  • Returns face bounding box → horizontal centre  │
  └───────────────────────┬───────────────────────────┘
                          │
          ▼
  ┌───────────────────────────────────────────────────┐
  │  Exponential Moving Average Smoothing             │
  │  • Interpolates between detections                │
  │  • Max drift cap → no jarring snaps               │
  │  • Max jump guard → ignores stray faces           │
  └───────────────────────┬───────────────────────────┘
                          │
          ▼
  ┌───────────────────────────────────────────────────┐
  │  9:16 Crop Window                                 │
  │  • Centred on smoothed face position              │
  │  • Scales to exactly 1080×1920 (Lanczos)         │
  └───────────────────────┬───────────────────────────┘
                          │
          ▼
  ┌───────────────────────────────────────────────────┐
  │  FFmpeg H.264 Encoder   CRF-18  (near-lossless)  │
  │  + Two-step seek audio extraction                 │
  │    → Fast keyframe seek + accurate micro-seek     │
  │    → Guarantees perfect audio/video sync          │
  └───────────────────────┬───────────────────────────┘
                          │
          ▼
  Portrait HD segments  (1080×1920, 9:16)  ✅
  Ready for TikTok · Instagram Reels · YouTube Shorts
```

---

## ⌨️ Command Line

For power users and automation:

```bash
# Basic
portrait-split-cli -i ~/Videos/conference.mp4

# Full control
portrait-split-cli \
  -i  ~/Videos/conference.mp4 \
  -o  ~/Videos/portrait_out \
  -n  "Speaker Name — Event 2026" \
  -s  200 \
  --parallel   4 \
  --smooth     0.3 \
  --crf        18 \
  --preset     fast \
  --max-jump   400 \
  --max-drift  6
```

### All flags

```
-i, --input         Source MP4 file                     [required]
-o, --output        Output folder                       [auto-named]
-n, --name          Base filename for output parts      [source stem]
-s, --segment       Segment length in seconds           [200]
    --parallel      Segments to process at once         [4]
    --smooth        Camera tracking 0.1–1.0             [0.3]
    --crf           H.264 quality 0–51                  [18]
    --preset        Encoding speed                      [fast]
    --max-jump      Ignore faces N px from focus        [400]
    --max-drift     Max pan speed px/frame              [6]
    --detect-every  Run detector every N frames         [5]
    --detect-scale  Downsample for detection            [0.25]
```

---

## 📋 Requirements

- **OS**: Ubuntu 20.04 / 22.04 / 24.04 (or any Debian-based Linux)
- **CPU**: Any modern CPU — 4+ cores recommended for parallel processing
- **RAM**: 4 GB minimum, 8 GB recommended for 4 parallel segments
- **Disk**: ~200 MB for install + space for your output videos
- **ffmpeg**: Installed automatically

---

## 🗑️ Uninstall

```bash
rm -rf ~/.portrait_split
sudo rm -f /usr/local/bin/portrait-split /usr/local/bin/portrait-split-cli
rm -f ~/.local/share/applications/portrait-split.desktop
```

---

## 🤝 Contributing

Pull requests welcome. Areas that would make this even better:

- **GPU acceleration** via CUDA / VideoToolbox
- **DNN face detector** for better accuracy on side-profile faces  
- **Windows / macOS** installer
- **Progress percentage** in the GUI (requires frame-count pre-scan)

---

## 📄 License

MIT — free to use, fork, modify, and distribute.

Built with ❤️ in Uganda by [AutoPro UG](https://github.com/autopro-ug).

---

<div align="center">

**If Portrait Split saved you hours of manual work, give it a ⭐ on GitHub!**

</div>
