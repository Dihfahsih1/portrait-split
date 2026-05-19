<div align="center">

<br/>

```
██████╗ ██╗ ██████╗ ██╗████████╗ █████╗ ██╗      ██████╗██╗  ██╗██╗   ██╗██████╗  ██████╗██╗  ██╗
██╔══██╗██║██╔════╝ ██║╚══██╔══╝██╔══██╗██║     ██╔════╝██║  ██║██║   ██║██╔══██╗██╔════╝██║  ██║
██║  ██║██║██║  ███╗██║   ██║   ███████║██║     ██║     ███████║██║   ██║██████╔╝██║     ███████║
██║  ██║██║██║   ██║██║   ██║   ██╔══██║██║     ██║     ██╔══██║██║   ██║██╔══██╗██║     ██╔══██║
██████╔╝██║╚██████╔╝██║   ██║   ██║  ██║███████╗╚██████╗██║  ██║╚██████╔╝██║  ██║╚██████╗██║  ██║
╚═════╝ ╚═╝ ╚═════╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
```

### ✦ The complete church media toolkit — portrait reframe · video slicing · YouTube clipping

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-6C63FF.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=for-the-badge&logo=windows)](https://github.com/Dihfahsih1/portrait-split)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Powered-007808?style=for-the-badge&logo=ffmpeg)](https://ffmpeg.org)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-YouTube-red?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)

<br/>

**[Install — Windows](#-install--windows)** · **[Install — Linux](#-install--linux)** · **[Tools](#-whats-included)** · **[How It Works](#-how-it-works)** · **[CLI Reference](#%EF%B8%8F-command-line)**

<br/>

---

</div>

## ✦ What Is DIGITALCHURCH DC?

You recorded a 3-hour sermon, seminar, or conference. Now you want to:

- Put it on **TikTok, Instagram Reels, or YouTube Shorts** — but it's landscape (16:9) and the speaker will be half off-screen
- **Clip a specific moment** from your recording or a YouTube video — without downloading the whole thing

**DIGITALCHURCH DC** is the unified launcher for two tools that handle both jobs automatically, from a single clean desktop app.

<br/>

---

## 🧰 What's Included

<table>
<tr>
<td width="50%" valign="top">

### 📐 Portrait Split
**Face-tracked 9:16 reframe**

| | |
|---|---|
| 🎯 **Face tracking** | OpenCV detects the speaker every few frames |
| 🎬 **Smart reframe** | Follows the face with smooth motion — no jarring snaps |
| 📱 **Full HD output** | 1080×1920 — not a tiny crop, true HD portrait |
| ✂️ **Auto-split** | Cuts into segments for TikTok / Reels / Shorts |
| ⚡ **Parallel encoding** | 4 segments at once — dramatically faster |
| 🔊 **Perfect audio sync** | Two-step seek guarantees lips and words always match |

</td>
<td width="50%" valign="top">

### ✂ VideoSlicer
**Precision video cutter**

| | |
|---|---|
| 🎞 **Local files** | Drop any MP4 / MKV / MOV and scrub it live |
| ▶️ **YouTube URLs** | Paste a URL — preview and clip without a full download |
| 👁 **Live preview** | Built-in player with scrub bar — click to set markers |
| ⬅➡ **Visual markers** | Set Start and End by clicking in the video — no typing |
| 🚫 **Zero quality loss** | FFmpeg stream-copy — original codec untouched |
| 🚀 **Parallel fragments** | yt-dlp fetches 8 fragments at once to beat throttling |

</td>
</tr>
</table>

<br/>

---

## 📥 Install — Windows

> Requires Windows 10 or 11. No prior software needed — the installer handles Python and ffmpeg automatically.

**Option A — One double-click (recommended)**

1. Download **[install.bat](install.bat)** from this repo
2. Double-click it
3. Follow the on-screen prompts — takes about 3–5 minutes

**Option B — If you already have Python 3.9+**

```powershell
python install.py
```

After install, search **"DIGITALCHURCH DC"** in your Start Menu, or run `digitalchurch` in any terminal.

<br/>

---

## 📥 Install — Linux

> Requires Ubuntu 20.04 / 22.04 / 24.04 or any Debian-based distro. Takes about 2–3 minutes.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Dihfahsih1/portrait-split/main/install.sh)
```

The installer handles everything:

- ✅ Installs `ffmpeg`, Python dependencies, and system libraries
- ✅ Creates an isolated venv — won't touch your system Python
- ✅ Installs PyQt6 + multimedia support via apt (best quality) or pip as fallback
- ✅ Registers **DIGITALCHURCH DC**, **Portrait Split**, and **VideoSlicer** in your app menu
- ✅ Creates `digitalchurch`, `portrait-split`, `video-slicer`, and `portrait-split-cli` terminal commands

After install, search **"DIGITALCHURCH DC"** in your app launcher.

<br/>

---

## 🖥️ The DC Hub

Opening `digitalchurch` launches the **DC hub** — a single window with both tools as cards. Click either card to open that tool. Both can run simultaneously.

You can also open each tool directly:

| Command | What opens |
|---|---|
| `digitalchurch` | DC hub — choose your tool |
| `portrait-split` | Portrait Split GUI directly |
| `video-slicer` | VideoSlicer directly |
| `portrait-split-cli` | Portrait Split command line |

<br/>

---

## 📐 Using Portrait Split

### GUI

1. **Click the input zone** → pick your MP4 file
2. **Click the output zone** → pick where to save
3. Adjust settings if needed (defaults work great for most sermons)
4. **Hit Start** → watch it process live in the log tab

### Settings

| Setting | Default | What it does |
|---|---|---|
| **Segment length** | `200s` | Length of each output clip (3 min 20 s) |
| **Parallel segments** | `4` | Clips encoded simultaneously — more = faster, more CPU |
| **CRF quality** | `18` | 0 = lossless · 18 = near-lossless · 28 = good for web |
| **Encoding preset** | `fast` | Speed vs file size — `ultrafast` to `slow` |
| **Tracking speed** | `0.3` | `0.1` = cinematic drift · `1.0` = instant snap |
| **Max jump** | `400px` | Ignores faces far from the main speaker (e.g. interpreter off to side) |
| **Max drift** | `6px/frame` | Caps pan speed — prevents dizzying camera moves |

<br/>

---

## ✂ Using VideoSlicer

### Local files

1. Switch to the **📁 Local File** tab
2. Drop a video file into the zone (or click to browse)
3. The preview player loads automatically — scrub to find your clip
4. Click **⬅ Set Start** and **Set End ➡** to mark the range visually
5. Set output folder and filename, then **▶ Slice Video**

### YouTube URLs

1. Switch to the **▶ YouTube URL** tab
2. Paste a YouTube URL
3. Click **⏵ Load Preview** — the video streams into the preview player (no full download)
4. Scrub, set your markers, then **▶ Slice Video** — only your clip is downloaded

> **Note:** Live preview requires `PyQt6-Qt6Multimedia`. The installer handles this. If unavailable, time inputs still work manually and slicing still runs.

<br/>

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
  │  • Scales to exactly 1080×1920 (Lanczos)          │
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

<br/>

---

## ⌨️ Command Line

For power users and automation:

```bash
# Basic
portrait-split-cli -i ~/Videos/sermon.mp4

# Full control
portrait-split-cli \
  -i  ~/Videos/sermon.mp4 \
  -o  ~/Videos/portrait_out \
  -n  "Pastor Name — Sunday Service 2026" \
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

<br/>

---

## 📋 Requirements

| | Linux | Windows |
|---|---|---|
| **OS** | Ubuntu 20.04 / 22.04 / 24.04 or Debian-based | Windows 10 or 11 (64-bit) |
| **Python** | 3.9+ (auto-installed if missing) | 3.9+ (auto-installed via winget) |
| **CPU** | Any modern CPU — 4+ cores recommended | Any modern CPU — 4+ cores recommended |
| **RAM** | 4 GB minimum · 8 GB for 4 parallel segments | 4 GB minimum · 8 GB for 4 parallel segments |
| **Disk** | ~300 MB install + output space | ~400 MB install + output space |
| **ffmpeg** | Auto-installed via apt | Auto-installed via winget |
| **GPU** | Not required | Not required |

<br/>

---

## 🗑️ Uninstall

**Linux**
```bash
rm -rf ~/.digitalchurch
sudo rm -f /usr/local/bin/digitalchurch
sudo rm -f /usr/local/bin/portrait-split
sudo rm -f /usr/local/bin/portrait-split-cli
sudo rm -f /usr/local/bin/video-slicer
rm -f ~/.local/share/applications/digitalchurch-dc.desktop
rm -f ~/.local/share/applications/portrait-split.desktop
rm -f ~/.local/share/applications/video-slicer.desktop
```

**Windows**

Delete the install folder:
```
%LOCALAPPDATA%\DigitalChurch\
```
Then remove the Start Menu folder: **Start → DigitalChurch DC → right-click any shortcut → Delete**.

<br/>

---

## 🤝 Contributing

Pull requests welcome. High-impact areas:

- **GPU acceleration** via CUDA / VideoToolbox for faster portrait encoding
- **DNN face detector** for better accuracy on side-profile and low-light faces
- **macOS installer** — the tools run on Mac, the installer just needs porting
- **Progress percentage** in Portrait Split GUI (requires frame-count pre-scan)
- **Batch YouTube clipping** — queue multiple URLs and time ranges in VideoSlicer

<br/>

---

## 📄 License

MIT — free to use, fork, modify, and distribute.

Built with ❤️ in Uganda by [Dihfahsih](https://dihfahsih.com).

---

<div align="center">

**If DIGITALCHURCH DC saved your media team hours of work, give it a ⭐ on GitHub!**

</div>