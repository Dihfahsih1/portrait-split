#!/usr/bin/env python3
"""
VideoSlicer  v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Precision video cutter — local files or YouTube, zero quality loss.
Uses FFmpeg -c copy so the original codec/resolution is untouched.

New in v2.0:
  • In-app video preview with scrub bar (local files)
  • Click-to-set Start / End markers directly from the timeline
  • YouTube: --concurrent-fragments 8 to break throttling

Install: pip install PyQt6 yt-dlp
         (also needs PyQt6-Qt6Multimedia for video preview)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRect, QSize,
    Qt, QThread, QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QFont,
    QFontMetrics, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPalette, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QSlider,
)

# Optional — gracefully disabled if PyQt6-Qt6Multimedia not installed
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

# ── Palette ────────────────────────────────────────────────────────
BG       = "#080C14"
SURFACE  = "#0D1421"
CARD     = "#111827"
CARD2    = "#161D2E"
BORDER   = "#1E2840"
BORDER2  = "#2A3550"
ACCENT   = "#F59E0B"
ACCENT_D = "#B45309"
ACCENT_L = "#FCD34D"
BLUE     = "#3B82F6"
TEXT     = "#F1F5F9"
MUTED    = "#64748B"
MUTED2   = "#94A3B8"
SUCCESS  = "#10B981"
DANGER   = "#EF4444"
WARN     = "#F59E0B"

FONT_MAIN = "Segoe UI" if sys.platform == "win32" else "Ubuntu"
FONT_MONO = "Consolas"  if sys.platform == "win32" else "Ubuntu Mono"

# ── Global stylesheet ─────────────────────────────────────────────
QSS = f"""
QMainWindow {{ background: {BG}; }}
QWidget#root {{ background: {BG}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: {SURFACE}; width: 6px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER2}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QLabel {{ color: {TEXT}; background: transparent; }}
QLineEdit {{
    background: {SURFACE};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    color: {TEXT};
    padding: 9px 14px;
    font-family: "{FONT_MONO}";
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QLineEdit:focus {{ border: 1.5px solid {ACCENT}; background: #0F1829; }}
QLineEdit:hover {{ border: 1.5px solid {BORDER2}; }}
QLineEdit[readOnly="true"] {{ color: {MUTED2}; background: {CARD}; }}
QTextEdit {{
    background: #050810;
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: #7EE787;
    font-family: "{FONT_MONO}";
    font-size: 11px;
    padding: 8px;
    selection-background-color: {BLUE};
}}
QProgressBar {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ACCENT_D}, stop:1 {ACCENT_L});
    border-radius: 6px;
}}
QSlider::groove:horizontal {{
    background: {BORDER};
    height: 4px;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_L};
    border: 2px solid {ACCENT_D};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: white;
}}
QToolTip {{
    background: {CARD2};
    color: {TEXT};
    border: 1px solid {BORDER2};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}
"""


# ── Helpers ────────────────────────────────────────────────────────

def hms_to_sec(s: str) -> float:
    s = s.strip()
    p = s.split(":")
    try:
        if len(p) == 3:   return int(p[0])*3600 + int(p[1])*60 + float(p[2])
        elif len(p) == 2: return int(p[0])*60 + float(p[1])
        else:             return float(s)
    except ValueError:
        raise ValueError(f"Bad time format: '{s}' — use HH:MM:SS")

def sec_to_hms(sec: float) -> str:
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def duration_label(sec: float) -> str:
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# ── Worker thread ──────────────────────────────────────────────────

class Worker(QThread):
    log      = pyqtSignal(str, str)
    progress = pyqtSignal(float)
    status   = pyqtSignal(str, str)
    done     = pyqtSignal(bool, str)

    def __init__(self, task: dict):
        super().__init__()
        self._task   = task
        self._cancel = False
        self._proc   = None

    def cancel(self):
        self._cancel = True
        if self._proc:
            try: self._proc.terminate()
            except Exception: pass

    def run(self):
        try:
            out = self._execute()
            if not self._cancel:
                self.done.emit(True, out)
        except Exception as e:
            self.log.emit(f"\n✗  {e}", DANGER)
            self.done.emit(False, "")

    def _execute(self) -> str:
        t      = self._task
        mode   = t["mode"]
        t_from = hms_to_sec(t["from"])
        t_to   = hms_to_sec(t["to"])
        dur    = t_to - t_from
        if dur <= 0:
            raise ValueError("'To' time must be after 'From' time.")

        out_dir  = Path(t["out_dir"])
        name     = t["name"]
        if not name.lower().endswith(".mp4"):
            name += ".mp4"
        out_path = str(out_dir / name)
        out_dir.mkdir(parents=True, exist_ok=True)

        self.log.emit(f"{'─'*52}", MUTED)
        self.log.emit(f"  Range  : {sec_to_hms(t_from)} → {sec_to_hms(t_to)}"
                      f"  ({duration_label(dur)})", TEXT)
        self.log.emit(f"  Output : {out_path}", TEXT)
        self.log.emit(f"{'─'*52}\n", MUTED)

        if mode == "file":
            self._slice_local(t["source"], t_from, t_to, dur, out_path)
        else:
            self._slice_youtube(t["source"], t_from, t_to, dur, out_path)

        return out_path

    def _slice_local(self, src, t_from, t_to, dur, out):
        self.status.emit("Slicing …", ACCENT)
        self.log.emit("⚙  FFmpeg — stream copy (zero quality loss) …\n", MUTED)
        cmd = [
            "ffmpeg", "-y",
            "-i",  src,
            "-ss", str(t_from),
            "-to", str(t_to),
            "-c", "copy",
            out,
        ]
        self._run(cmd, dur)

    def _slice_youtube(self, url, t_from, t_to, dur, out):
        self.status.emit("Fetching from YouTube …", ACCENT)
        self.log.emit("⚙  yt-dlp — parallel fragments (8×), stream copy …\n", MUTED)

        section = f"*{sec_to_hms(t_from)}-{sec_to_hms(t_to)}"
        tmp = str(Path(out).parent / f"__tmp_{Path(out).stem}.%(ext)s")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--download-sections", section,
            # ── Speed fix: fetch 8 fragments in parallel ──────────
            # YouTube throttles each connection to ~playback bitrate.
            # --concurrent-fragments breaks past that by opening N
            # simultaneous connections, so a 37-min clip takes ~5 min
            # instead of ~37 min on a fast line.
            "--concurrent-fragments", "8",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--no-part",
            "-o", tmp,
            "--newline",
            url,
        ]
        self._run(cmd, dur, mode="ytdlp")

        tmp_resolved = str(Path(out).parent / f"__tmp_{Path(out).stem}.mp4")
        if Path(tmp_resolved).exists():
            try: os.replace(tmp_resolved, out)
            except Exception: pass

    def _run(self, cmd, duration, mode="ffmpeg"):
        self.log.emit("  $ " + " ".join(
            f'"{c}"' if " " in str(c) else str(c) for c in cmd
        ) + "\n", MUTED)

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
            )
        except FileNotFoundError:
            raise ValueError(f"'{cmd[0]}' not found — is it installed and in PATH?")

        _NOISE = re.compile(
            r"Late SEI is not implemented"
            r"|If you want to help, upload a sample"
            r"|ffmpeg-devel@ffmpeg"
            r"|streams\.videolan\.org"
            r"|Press \[q\] to stop"
            r"|\[h264 @.+\] Late"
            r"|using cpu capabilities"
            r"|profile High, level"
            r"|264 - core \d+"
            r"|options: cabac="
            r"|Side data:"
            r"|cpb: bitrate"
            r"|^\s+Metadata:"
            r"|^\s+major_brand\s*:"
            r"|^\s+minor_version\s*:"
            r"|^\s+compatible_brands:"
            r"|^\s+creation_time\s*:"
            r"|^\s+handler_name\s*:"
            r"|^\s+vendor_id\s*:"
            r"|^\s+encoder\s*:"
            r"|Input #\d+, mov,mp4"
            r"|from 'https://rr\d"
            r"|googlevideo\.com"
            r"|^\s+Duration: \d"
            r"|^\s+Stream #\d+:\d+\[0x"
            r"|Output #0, mp4"
            r"|encoder\s*: Lavf"
        )

        for line in self._proc.stdout:
            if self._cancel: break
            line = line.rstrip()
            if not line.strip() or _NOISE.search(line):
                continue

            if re.match(r"frame=\s*\d+", line):
                if mode == "ffmpeg":
                    m = re.search(r"time=(\d+):(\d+):([\d.]+)", line)
                    if m and duration > 0:
                        el  = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                        pct = min(el / duration * 100, 99)
                        self.progress.emit(pct)
                        self.status.emit(f"Processing … {pct:.0f}%", ACCENT)
                continue

            if mode == "ffmpeg":
                m = re.search(r"time=(\d+):(\d+):([\d.]+)", line)
                if m and duration > 0:
                    el  = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                    pct = min(el / duration * 100, 99)
                    self.progress.emit(pct)
                    self.status.emit(f"Processing … {pct:.0f}%", ACCENT)
            elif mode == "ytdlp":
                m = re.search(
                    r"\[download\]\s+([\d.]+)%"
                    r"(?:\s+of\s+~?([\d.]+\S+))?"
                    r"(?:\s+at\s+([\d.]+\S+/s))?"
                    r"(?:\s+ETA\s+(\S+))?", line)
                if m:
                    pct  = float(m.group(1))
                    size = m.group(2) or ""
                    spd  = m.group(3) or ""
                    eta  = m.group(4) or ""
                    self.progress.emit(pct * 0.95)
                    parts = [f"Downloading … {pct:.1f}%"]
                    if size: parts.append(f"of {size}")
                    if spd:  parts.append(f"at {spd}")
                    if eta:  parts.append(f"ETA {eta}")
                    self.status.emit("  ".join(parts), ACCENT)
                    self.log.emit(
                        f"  [download]  {pct:.1f}%"
                        + (f"  of {size}" if size else "")
                        + (f"  at {spd}"  if spd  else "")
                        + (f"  ETA {eta}" if eta  else ""),
                        ACCENT
                    )
                    continue

            col = DANGER if "error" in line.lower() else "#7EE787"
            self.log.emit("  " + line, col)

        self._proc.wait()
        rc = self._proc.returncode
        self._proc = None
        if not self._cancel and rc not in (0, None):
            raise ValueError(f"Process exited with code {rc}")


# ── YouTube URL fetcher (for preview) ─────────────────────────────

class YtFetchUrlWorker(QThread):
    """Uses yt-dlp --get-url to resolve a direct streamable URL (no download)."""
    ready  = pyqtSignal(str)   # emits the direct stream URL
    failed = pyqtSignal(str)   # emits error message

    def __init__(self, yt_url: str):
        super().__init__()
        self._yt_url = yt_url

    def run(self):
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "yt_dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "--get-url",
                    self._yt_url,
                ],
                capture_output=True, text=True, timeout=30,
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if lines:
                # First URL is the video stream; second (if present) is audio.
                # QMediaPlayer can handle a combined best[ext=mp4] URL directly.
                self.ready.emit(lines[0])
            else:
                err = result.stderr.strip().splitlines()
                self.failed.emit(err[-1] if err else "yt-dlp returned no URL")
        except subprocess.TimeoutExpired:
            self.failed.emit("Timed out fetching YouTube URL (30 s)")
        except Exception as e:
            self.failed.emit(str(e))


# ── Custom widgets ─────────────────────────────────────────────────

class Card(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 18)
        self._layout.setSpacing(12)
        if title:
            lbl = QLabel(title)
            lbl.setFont(QFont(FONT_MAIN, 8, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {MUTED}; letter-spacing: 2px;")
            self._layout.addWidget(lbl)

    def body(self):
        return self._layout


class GlowButton(QPushButton):
    def __init__(self, text, accent=True, danger=False, parent=None):
        super().__init__(text, parent)
        self._accent  = accent
        self._danger  = danger
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)
        self._style()

    def _style(self, hover=False):
        if self._danger:
            bg  = "#7F1D1D" if not hover else "#991B1B"
            fg  = DANGER
            brd = "#991B1B"
        elif self._accent:
            bg  = ACCENT if not hover else ACCENT_L
            fg  = "#0A0A0A"
            brd = ACCENT
        else:
            bg  = CARD2 if not hover else BORDER
            fg  = MUTED2
            brd = BORDER2
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1.5px solid {brd};
                border-radius: 8px;
                font-family: "{FONT_MAIN}";
                font-size: 13px;
                font-weight: 700;
                padding: 0 22px;
            }}
        """)

    def enterEvent(self, e):
        self._style(hover=True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._style(hover=False)
        super().leaveEvent(e)


class SmallButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {CARD2};
                color: {MUTED2};
                border: 1px solid {BORDER2};
                border-radius: 7px;
                font-family: "{FONT_MAIN}";
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {BORDER};
                color: {TEXT};
                border: 1px solid {ACCENT};
            }}
        """)


class MarkerButton(QPushButton):
    """Colored marker-set button (Start = green tint, End = red tint)."""
    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        self._color = color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1.5px solid {color};
                border-radius: 6px;
                font-family: "{FONT_MAIN}";
                font-size: 11px;
                font-weight: 700;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {color}22;
            }}
            QPushButton:pressed {{
                background: {color}44;
            }}
        """)


class TabPill(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, options: list, parent=None):
        super().__init__(parent)
        self._options = options
        self._active  = options[0][1]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._btns = {}
        for label, val in options:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(True)
            b.setFixedHeight(34)
            b.clicked.connect(lambda _, v=val: self._select(v))
            self._btns[val] = b
            lay.addWidget(b)
        lay.addStretch()
        self._refresh()

    def _select(self, val):
        self._active = val
        self._refresh()
        self.changed.emit(val)

    def _refresh(self):
        for val, b in self._btns.items():
            active = val == self._active
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {"" + ACCENT if active else CARD2};
                    color: {"#0A0A0A" if active else MUTED2};
                    border: 1.5px solid {"" + ACCENT if active else BORDER2};
                    border-radius: 7px;
                    font-family: "{FONT_MAIN}";
                    font-size: 12px;
                    font-weight: {"700" if active else "500"};
                    padding: 0 18px;
                }}
            """)
            b.setChecked(active)

    def value(self): return self._active


class DropZone(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._idle()

    def _idle(self):
        self.setText("📂  Drop video here  or  click to browse")
        self._set_style(False)

    def _set_style(self, active: bool):
        col = ACCENT if active else BORDER2
        self.setStyleSheet(f"""
            QLabel {{
                background: {"rgba(245,158,11,0.06)" if active else SURFACE};
                border: 2px dashed {col};
                border-radius: 10px;
                color: {MUTED2 if not active else ACCENT};
                font-family: "{FONT_MAIN}";
                font-size: 13px;
                padding: 12px;
            }}
        """)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_style(True)

    def dragLeaveEvent(self, e):
        self._set_style(False)

    def dropEvent(self, e: QDropEvent):
        self._set_style(False)
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._show_file(path)
            self.file_dropped.emit(path)

    def mousePressEvent(self, e):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select video file",
            str(Path.home() / "Desktop"),
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts *.m4v);;All Files (*)",
        )
        if path:
            self._show_file(path)
            self.file_dropped.emit(path)

    def _show_file(self, path: str):
        name = Path(path).name
        size = Path(path).stat().st_size / (1024**3)
        self.setText(f"✅  {name}\n{size:.2f} GB")
        self.setStyleSheet(f"""
            QLabel {{
                background: rgba(16,185,129,0.06);
                border: 2px solid {SUCCESS};
                border-radius: 10px;
                color: {SUCCESS};
                font-family: "{FONT_MONO}";
                font-size: 12px;
                padding: 12px;
            }}
        """)


class TimeInput(QWidget):
    changed = pyqtSignal()

    def __init__(self, label: str, default="00:00:00", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        lbl = QLabel(label)
        lbl.setFont(QFont(FONT_MAIN, 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {MUTED}; letter-spacing: 1.5px;")
        lay.addWidget(lbl)

        self._edit = QLineEdit(default)
        self._edit.setPlaceholderText("HH:MM:SS")
        self._edit.setFixedHeight(44)
        self._edit.setFont(QFont(FONT_MONO, 15, QFont.Weight.Bold))
        self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit.textChanged.connect(self._validate)
        self._edit.textChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self._edit)

    def _validate(self, text):
        try:
            hms_to_sec(text)
            self._edit.setStyleSheet(f"""
                QLineEdit {{
                    background: {SURFACE};
                    border: 1.5px solid {BORDER};
                    border-radius: 8px;
                    color: {ACCENT_L};
                    padding: 9px 14px;
                    font-family: "{FONT_MONO}";
                    font-size: 15px;
                    font-weight: 700;
                    text-align: center;
                }}
                QLineEdit:focus {{ border: 1.5px solid {ACCENT}; background: #0F1829; }}
            """)
        except Exception:
            self._edit.setStyleSheet(f"""
                QLineEdit {{
                    background: rgba(239,68,68,0.08);
                    border: 1.5px solid {DANGER};
                    border-radius: 8px;
                    color: {DANGER};
                    padding: 9px 14px;
                    font-family: "{FONT_MONO}";
                    font-size: 15px;
                    font-weight: 700;
                    text-align: center;
                }}
            """)

    def value(self): return self._edit.text().strip()
    def set_value(self, v): self._edit.setText(v)


# ── Video Preview Widget ───────────────────────────────────────────

class VideoPreview(QWidget):
    """
    Inline video player with scrub bar and start/end marker buttons.
    Requires PyQt6-Qt6Multimedia. Hidden automatically if unavailable.
    """
    start_set = pyqtSignal(str)   # emits HH:MM:SS
    end_set   = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration_ms = 0
        self._dragging    = False
        self._loaded      = False

        self.setStyleSheet(f"background: {CARD}; border-radius: 10px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 14)
        lay.setSpacing(8)

        # header
        hdr = QHBoxLayout()
        title = QLabel("PREVIEW")
        title.setFont(QFont(FONT_MAIN, 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {MUTED}; letter-spacing: 2px;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._pos_lbl = QLabel("00:00:00 / 00:00:00")
        self._pos_lbl.setFont(QFont(FONT_MONO, 9))
        self._pos_lbl.setStyleSheet(f"color: {MUTED2};")
        hdr.addWidget(self._pos_lbl)
        lay.addLayout(hdr)

        if HAS_MULTIMEDIA:
            # video surface
            self._video = QVideoWidget()
            self._video.setMinimumHeight(260)
            self._video.setStyleSheet("background: #000; border-radius: 8px;")
            lay.addWidget(self._video)

            # media player
            self._player = QMediaPlayer()
            self._audio  = QAudioOutput()
            self._audio.setVolume(0.5)
            self._player.setAudioOutput(self._audio)
            self._player.setVideoOutput(self._video)
            self._player.positionChanged.connect(self._on_position)
            self._player.durationChanged.connect(self._on_duration)

        else:
            no_lbl = QLabel(
                "⚠  PyQt6-Qt6Multimedia not installed\n"
                "    pip install PyQt6-Qt6Multimedia\n"
                "    (time inputs still work manually)"
            )
            no_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_lbl.setMinimumHeight(160)
            no_lbl.setFont(QFont(FONT_MAIN, 10))
            no_lbl.setStyleSheet(
                f"color: {MUTED}; background: {SURFACE}; "
                f"border-radius: 8px; border: 1px dashed {BORDER2}; padding: 12px;"
            )
            lay.addWidget(no_lbl)

        # ── scrub bar with overlay markers ────────────────────────
        self._scrub = QSlider(Qt.Orientation.Horizontal)
        self._scrub.setRange(0, 10000)
        self._scrub.setValue(0)
        self._scrub.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scrub.sliderPressed.connect(self._on_scrub_press)
        self._scrub.sliderMoved.connect(self._on_scrub_move)
        self._scrub.sliderReleased.connect(self._on_scrub_release)
        lay.addWidget(self._scrub)

        # ── control row ───────────────────────────────────────────
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self._play_btn = SmallButton("▶  Play")
        self._play_btn.setFixedWidth(90)
        self._play_btn.clicked.connect(self._toggle_play)
        ctrl.addWidget(self._play_btn)

        # volume
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(50)
        self._vol_slider.setFixedWidth(70)
        self._vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vol_slider.setToolTip("Volume")
        if HAS_MULTIMEDIA:
            self._vol_slider.valueChanged.connect(
                lambda v: self._audio.setVolume(v / 100.0))
        ctrl.addWidget(self._vol_slider)

        ctrl.addStretch()

        # markers
        self._set_start_btn = MarkerButton("⬅  Set Start", SUCCESS)
        self._set_start_btn.setToolTip("Use current position as clip start")
        self._set_start_btn.clicked.connect(self._set_start)
        ctrl.addWidget(self._set_start_btn)

        self._set_end_btn = MarkerButton("Set End  ➡", DANGER)
        self._set_end_btn.setToolTip("Use current position as clip end")
        self._set_end_btn.clicked.connect(self._set_end)
        ctrl.addWidget(self._set_end_btn)

        lay.addLayout(ctrl)

        # ── marker position labels ────────────────────────────────
        mrow = QHBoxLayout()
        self._start_marker_lbl = QLabel("▶ Start: —")
        self._start_marker_lbl.setFont(QFont(FONT_MONO, 9))
        self._start_marker_lbl.setStyleSheet(f"color: {SUCCESS};")
        self._end_marker_lbl = QLabel("⏹ End: —")
        self._end_marker_lbl.setFont(QFont(FONT_MONO, 9))
        self._end_marker_lbl.setStyleSheet(f"color: {DANGER};")
        mrow.addWidget(self._start_marker_lbl)
        mrow.addStretch()
        mrow.addWidget(self._end_marker_lbl)
        lay.addLayout(mrow)

        # ── position update timer ─────────────────────────────────
        self._timer = QTimer()
        self._timer.setInterval(250)
        if HAS_MULTIMEDIA:
            self._timer.timeout.connect(self._sync_scrub)
        self._timer.start()

    # ── public API ────────────────────────────────────────────────

    def load(self, path: str):
        if not HAS_MULTIMEDIA:
            return
        self._loaded = True
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.pause()
        self._play_btn.setText("▶  Play")

    def load_url(self, url: str):
        """Load a remote/streaming URL (e.g. direct YouTube stream) into the player."""
        if not HAS_MULTIMEDIA:
            return
        self._loaded = True
        self._player.setSource(QUrl(url))
        self._player.pause()
        self._play_btn.setText("▶  Play")

    def unload(self):
        if not HAS_MULTIMEDIA:
            return
        self._loaded = False
        self._player.stop()
        self._player.setSource(QUrl())
        self._scrub.setValue(0)
        self._pos_lbl.setText("00:00:00 / 00:00:00")
        self._play_btn.setText("▶  Play")
        self._start_marker_lbl.setText("▶ Start: —")
        self._end_marker_lbl.setText("⏹ End: —")

    # ── slots ─────────────────────────────────────────────────────

    def _toggle_play(self):
        if not HAS_MULTIMEDIA or not self._loaded:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_btn.setText("▶  Play")
        else:
            self._player.play()
            self._play_btn.setText("⏸  Pause")

    def _on_position(self, ms: int):
        pos_s = ms / 1000.0
        dur_s = self._duration_ms / 1000.0
        self._pos_lbl.setText(f"{sec_to_hms(pos_s)} / {sec_to_hms(dur_s)}")

    def _on_duration(self, ms: int):
        self._duration_ms = ms

    def _sync_scrub(self):
        if not HAS_MULTIMEDIA or not self._loaded or self._dragging:
            return
        if self._duration_ms > 0:
            pos = self._player.position()
            val = int(pos / self._duration_ms * 10000)
            self._scrub.setValue(val)

    def _on_scrub_press(self):
        self._dragging = True
        if HAS_MULTIMEDIA:
            self._player.pause()

    def _on_scrub_move(self, val: int):
        if not HAS_MULTIMEDIA or not self._loaded or self._duration_ms == 0:
            return
        ms = int(val / 10000 * self._duration_ms)
        self._player.setPosition(ms)
        self._on_position(ms)

    def _on_scrub_release(self):
        self._dragging = False

    def _current_hms(self) -> str:
        if not HAS_MULTIMEDIA:
            return "00:00:00"
        ms = self._player.position()
        return sec_to_hms(ms / 1000.0)

    def _set_start(self):
        t = self._current_hms()
        self._start_marker_lbl.setText(f"▶ Start: {t}")
        self.start_set.emit(t)

    def _set_end(self):
        t = self._current_hms()
        self._end_marker_lbl.setText(f"⏹ End: {t}")
        self.end_set.emit(t)


# ── Main Window ────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoSlicer  v2")
        self.resize(780, 940)
        self.setMinimumSize(680, 760)
        self.setStyleSheet(QSS)

        self._worker        = None
        self._src_file      = ""
        self._yt_fetch_worker = None

        self._build()
        self._check_deps()

    # ── Build UI ──────────────────────────────────────────────────

    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── header ────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(72)
        hdr.setStyleSheet(f"""
            background: qlineargradient(
                x1:0,y1:0, x2:1,y2:0,
                stop:0 #0A0F1E, stop:0.6 #0D1628, stop:1 #0A1020
            );
            border-bottom: 1px solid {BORDER};
        """)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(28, 0, 28, 0)

        icon_lbl = QLabel("✂")
        icon_lbl.setFont(QFont(FONT_MAIN, 22))
        icon_lbl.setStyleSheet(f"color: {ACCENT};")
        hl.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        t1 = QLabel("VideoSlicer")
        t1.setFont(QFont(FONT_MAIN, 17, QFont.Weight.Bold))
        t1.setStyleSheet(f"color: {TEXT};")
        t2 = QLabel("preview · seek · set markers · zero quality loss")
        t2.setFont(QFont(FONT_MAIN, 9))
        t2.setStyleSheet(f"color: {MUTED};")
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        hl.addLayout(title_col)
        hl.addStretch()

        deps_col = QVBoxLayout()
        deps_col.setSpacing(2)
        deps_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._dep_ffmpeg = self._dep_badge("FFmpeg",  have("ffmpeg"))
        self._dep_ytdlp  = self._dep_badge("yt-dlp",
                            have("yt-dlp") or self._have_ytdlp_module())
        self._dep_media  = self._dep_badge("Preview", HAS_MULTIMEDIA)
        deps_col.addWidget(self._dep_ffmpeg)
        deps_col.addWidget(self._dep_ytdlp)
        deps_col.addWidget(self._dep_media)
        hl.addLayout(deps_col)

        outer.addWidget(hdr)

        # ── scrollable body ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        body = QWidget()
        body.setObjectName("root")
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # ── SOURCE card ───────────────────────────────────────────
        src_card = Card("SOURCE")
        lay.addWidget(src_card)
        sb = src_card.body()

        self._src_tab = TabPill([
            ("📁  Local File",  "file"),
            ("▶  YouTube URL", "youtube"),
        ])
        self._src_tab.changed.connect(self._toggle_src)
        sb.addWidget(self._src_tab)

        self._src_stack = QStackedWidget()
        sb.addWidget(self._src_stack)

        # page 0 — drop zone
        fp = QWidget()
        fp.setStyleSheet("background: transparent;")
        fl = QVBoxLayout(fp)
        fl.setContentsMargins(0, 0, 0, 0)
        self._drop = DropZone()
        self._drop.file_dropped.connect(self._on_file)
        fl.addWidget(self._drop)
        self._src_stack.addWidget(fp)

        # page 1 — youtube url
        yp = QWidget()
        yp.setStyleSheet("background: transparent;")
        yl = QVBoxLayout(yp)
        yl.setContentsMargins(0, 0, 0, 0)
        yl.setSpacing(8)

        yt_row = QHBoxLayout()
        yt_row.setSpacing(8)
        self._yt_edit = QLineEdit()
        self._yt_edit.setPlaceholderText("https://www.youtube.com/watch?v=…")
        self._yt_edit.setFixedHeight(44)
        yt_row.addWidget(self._yt_edit)

        self._yt_preview_btn = SmallButton("⏵  Load Preview")
        self._yt_preview_btn.setFixedHeight(44)
        self._yt_preview_btn.setFixedWidth(130)
        self._yt_preview_btn.clicked.connect(self._load_yt_preview)
        yt_row.addWidget(self._yt_preview_btn)
        yl.addLayout(yt_row)

        self._yt_status_lbl = QLabel("")
        self._yt_status_lbl.setFont(QFont(FONT_MONO, 9))
        self._yt_status_lbl.setStyleSheet(f"color: {MUTED};")
        self._yt_status_lbl.setWordWrap(True)
        yl.addWidget(self._yt_status_lbl)

        yl.addStretch()
        self._src_stack.addWidget(yp)

        # ── VIDEO PREVIEW ─────────────────────────────────────────
        self._preview = VideoPreview()
        self._preview.start_set.connect(self._on_preview_start)
        self._preview.end_set.connect(self._on_preview_end)
        self._preview.setVisible(False)   # shown only once a file is loaded
        lay.addWidget(self._preview)

        # ── TIME RANGE card ───────────────────────────────────────
        tr_card = Card("TIME RANGE")
        lay.addWidget(tr_card)
        tb = tr_card.body()

        hint_preview = QLabel(
            "💡  Load a local file or paste a YouTube URL and click  ⏵ Load Preview  "
            "→ scrub the video → click  ⬅ Set Start  and  Set End ➡  to fill these automatically"
        )
        hint_preview.setFont(QFont(FONT_MAIN, 9))
        hint_preview.setStyleSheet(f"color: {MUTED}; font-style: italic;")
        hint_preview.setWordWrap(True)
        tb.addWidget(hint_preview)

        tr_row = QHBoxLayout()
        tr_row.setSpacing(16)
        self._from = TimeInput("FROM", "00:00:00")
        self._to   = TimeInput("TO",   "00:00:00")
        self._from.changed.connect(self._update_dur)
        self._to.changed.connect(self._update_dur)
        tr_row.addWidget(self._from)

        arrow = QLabel("→")
        arrow.setFont(QFont(FONT_MAIN, 20))
        arrow.setStyleSheet(f"color: {BORDER2};")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedWidth(32)
        arrow.setContentsMargins(0, 18, 0, 0)
        tr_row.addWidget(arrow)
        tr_row.addWidget(self._to)
        tb.addLayout(tr_row)

        self._dur_lbl = QLabel("Duration: —")
        self._dur_lbl.setFont(QFont(FONT_MAIN, 10))
        self._dur_lbl.setStyleSheet(f"color: {MUTED};")
        tb.addWidget(self._dur_lbl)

        hint = QLabel("Examples:  02:04:10  ·  1:30:00  ·  45:30  ·  3720")
        hint.setFont(QFont(FONT_MONO, 9))
        hint.setStyleSheet(f"color: {MUTED};")
        tb.addWidget(hint)

        # ── OUTPUT card ───────────────────────────────────────────
        out_card = Card("OUTPUT")
        lay.addWidget(out_card)
        ob = out_card.body()

        fol_row = QHBoxLayout()
        fol_row.setSpacing(8)
        self._out_edit = QLineEdit(str(Path.home() / "Desktop"))
        self._out_edit.setFixedHeight(40)
        fol_row.addWidget(self._out_edit)
        fol_btn = SmallButton("Browse")
        fol_btn.setFixedWidth(80)
        fol_btn.clicked.connect(self._browse_out)
        fol_row.addWidget(fol_btn)
        ob.addLayout(fol_row)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_lbl = QLabel("Filename:")
        name_lbl.setFont(QFont(FONT_MAIN, 10))
        name_lbl.setStyleSheet(f"color: {MUTED2};")
        name_lbl.setFixedWidth(80)
        name_row.addWidget(name_lbl)
        self._name_edit = QLineEdit("clip_output.mp4")
        self._name_edit.setFixedHeight(40)
        name_row.addWidget(self._name_edit)
        ob.addLayout(name_row)

        # ── Action row ────────────────────────────────────────────
        act = QHBoxLayout()
        act.setSpacing(10)
        self._run_btn = GlowButton("▶   Slice Video", accent=True)
        self._run_btn.setFixedHeight(50)
        self._run_btn.setFont(QFont(FONT_MAIN, 13, QFont.Weight.Bold))
        self._run_btn.clicked.connect(self._start)
        act.addWidget(self._run_btn)

        self._cancel_btn = GlowButton("✕  Cancel", danger=True)
        self._cancel_btn.setFixedWidth(110)
        self._cancel_btn.setFixedHeight(50)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        act.addWidget(self._cancel_btn)
        lay.addLayout(act)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont(FONT_MAIN, 10))
        self._status_lbl.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(self._status_lbl)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(12)
        self._progress.setTextVisible(False)
        self._progress.setValue(0)
        lay.addWidget(self._progress)

        # ── Log card ──────────────────────────────────────────────
        log_card = Card("LOG")
        lay.addWidget(log_card)
        lb = log_card.body()

        clr_row = QHBoxLayout()
        clr_row.addStretch()
        clr_btn = SmallButton("Clear")
        clr_btn.setFixedWidth(64)
        clr_btn.clicked.connect(self._clear_log)
        clr_row.addWidget(clr_btn)
        lb.addLayout(clr_row)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(150)
        lb.addWidget(self._log)

        lay.addSpacing(8)

    # ── Helpers ───────────────────────────────────────────────────

    def _dep_badge(self, name, ok):
        col = SUCCESS if ok else DANGER
        sym = "✔" if ok else "✗"
        lbl = QLabel(f"{sym}  {name}")
        lbl.setFont(QFont(FONT_MONO, 9))
        lbl.setStyleSheet(f"color: {col};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        return lbl

    def _have_ytdlp_module(self):
        try:
            import yt_dlp
            return True
        except ImportError:
            return False

    def _toggle_src(self, val):
        self._src_stack.setCurrentIndex(0 if val == "file" else 1)
        # unload preview only when switching away from youtube (to file), not the other way
        if val == "file":
            self._preview.unload()
            self._preview.setVisible(False)
            self._yt_status_lbl.setText("")

    def _load_yt_preview(self):
        url = self._yt_edit.text().strip()
        if not url.startswith("http"):
            self._yt_status_lbl.setStyleSheet(f"color: {DANGER};")
            self._yt_status_lbl.setText("⚠  Enter a valid YouTube URL first.")
            return
        if not HAS_MULTIMEDIA:
            self._yt_status_lbl.setStyleSheet(f"color: {WARN};")
            self._yt_status_lbl.setText(
                "⚠  Preview unavailable — install PyQt6-Qt6Multimedia"
            )
            return

        self._yt_preview_btn.setEnabled(False)
        self._yt_status_lbl.setStyleSheet(f"color: {ACCENT};")
        self._yt_status_lbl.setText("⏳  Resolving stream URL via yt-dlp…")
        self._preview.unload()
        self._preview.setVisible(False)

        self._yt_fetch_worker = YtFetchUrlWorker(url)
        self._yt_fetch_worker.ready.connect(self._on_yt_preview_ready)
        self._yt_fetch_worker.failed.connect(self._on_yt_preview_failed)
        self._yt_fetch_worker.start()

    def _on_yt_preview_ready(self, stream_url: str):
        self._yt_preview_btn.setEnabled(True)
        self._yt_status_lbl.setStyleSheet(f"color: {SUCCESS};")
        self._yt_status_lbl.setText("✔  Stream resolved — scrub below to set markers")
        # derive a filename from the URL if output name is still default
        if self._name_edit.text() == "clip_output.mp4":
            self._name_edit.setText("youtube_clip.mp4")
        self._preview.setVisible(True)
        self._preview.load_url(stream_url)

    def _on_yt_preview_failed(self, err: str):
        self._yt_preview_btn.setEnabled(True)
        self._yt_status_lbl.setStyleSheet(f"color: {DANGER};")
        self._yt_status_lbl.setText(f"✗  {err}")

    def _on_file(self, path: str):
        self._src_file = path
        stem = Path(path).stem
        self._name_edit.setText(f"{stem}_clip.mp4")
        # show and load the preview player
        self._preview.setVisible(True)
        self._preview.load(path)

    def _on_preview_start(self, t: str):
        """Called when user clicks ⬅ Set Start in the preview."""
        self._from.set_value(t)

    def _on_preview_end(self, t: str):
        """Called when user clicks Set End ➡ in the preview."""
        self._to.set_value(t)

    def _update_dur(self):
        try:
            d = hms_to_sec(self._to.value()) - hms_to_sec(self._from.value())
            if d > 0:
                self._dur_lbl.setText(f"Duration: {duration_label(d)}")
                self._dur_lbl.setStyleSheet(f"color: {ACCENT};")
            else:
                self._dur_lbl.setText("Duration: —  (check times)")
                self._dur_lbl.setStyleSheet(f"color: {DANGER};")
        except Exception:
            self._dur_lbl.setText("Duration: —")
            self._dur_lbl.setStyleSheet(f"color: {MUTED};")

    def _browse_out(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select output folder",
            self._out_edit.text() or str(Path.home() / "Desktop"),
        )
        if folder:
            self._out_edit.setText(folder)

    def _log_line(self, msg: str, colour: str = None):
        col = colour or "#7EE787"
        self._log.setTextColor(QColor(col))
        self._log.append(msg)
        self._log.ensureCursorVisible()

    def _clear_log(self):
        self._log.clear()

    def _set_status(self, msg: str, col: str = MUTED):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {col};")

    def _check_deps(self):
        missing = []
        if not have("ffmpeg"):
            missing.append("FFmpeg  →  https://ffmpeg.org/download.html")
        if not (have("yt-dlp") or self._have_ytdlp_module()):
            missing.append("yt-dlp  →  pip install yt-dlp")
        if not HAS_MULTIMEDIA:
            missing.append("Preview →  pip install PyQt6-Qt6Multimedia")
        if missing:
            self._log_line("⚠  Missing optional tools:", WARN)
            for m in missing:
                self._log_line(f"   • {m}", MUTED2)
            self._log_line("", None)
        else:
            self._log_line("✔  All dependencies found — ready.", SUCCESS)

    # ── Run / Cancel ──────────────────────────────────────────────

    def _start(self):
        if self._worker and self._worker.isRunning():
            return

        mode = self._src_tab.value()
        src  = self._src_file if mode == "file" else self._yt_edit.text().strip()

        if not src:
            self._set_status("No source selected.", DANGER)
            return
        if mode == "file" and not Path(src).is_file():
            self._set_status("File not found.", DANGER)
            return
        if mode == "youtube" and not src.startswith("http"):
            self._set_status("Enter a valid YouTube URL.", DANGER)
            return

        task = {
            "mode":    mode,
            "source":  src,
            "from":    self._from.value(),
            "to":      self._to.value(),
            "out_dir": self._out_edit.text().strip(),
            "name":    self._name_edit.text().strip(),
        }

        self._worker = Worker(task)
        self._worker.log.connect(self._log_line)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._set_status)
        self._worker.done.connect(self._on_done)

        self._set_working(True)
        self._progress.setRange(0, 0)
        self._log_line(f"\n⚡  Starting …", ACCENT)
        self._worker.start()

    def _on_progress(self, pct: float):
        if self._progress.maximum() == 0:
            self._progress.setRange(0, 100)
        self._progress.setValue(int(pct))

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._set_status("Cancelled.", DANGER)
        self._set_working(False)

    def _on_done(self, ok: bool, out: str):
        self._set_working(False)
        self._progress.setRange(0, 100)
        if ok:
            self._progress.setValue(100)
            self._log_line(f"\n✅  Saved to: {out}", SUCCESS)
            self._set_status("Done! ✓", SUCCESS)
            self._show_done_overlay(out)
        else:
            self._progress.setValue(0)

    def _set_working(self, busy: bool):
        self._cancel_btn.setEnabled(busy)
        if busy:
            self._run_btn.setEnabled(False)
            self._run_btn.setText("⏳  Slicing…")
            self._run_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {BORDER};
                    color: {MUTED};
                    border: 1.5px solid {BORDER2};
                    border-radius: 8px;
                    font-family: "{FONT_MAIN}";
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0 22px;
                }}
            """)
        else:
            self._run_btn.setEnabled(True)
            self._run_btn.setText("▶   Slice Video")
            self._run_btn._style()

    def _show_done_overlay(self, path: str):
        from PyQt6.QtWidgets import QMessageBox
        mb = QMessageBox(self)
        mb.setWindowTitle("Done!")
        mb.setText(f"<b style='color:#10B981;font-size:15px'>✅  Clip saved!</b>")
        mb.setInformativeText(path)
        mb.setStyleSheet(f"""
            QMessageBox {{ background: {CARD}; color: {TEXT}; font-family: "{FONT_MAIN}"; }}
            QLabel {{ color: {TEXT}; }}
            QPushButton {{
                background: {ACCENT}; color: {BG};
                border: none; border-radius: 6px;
                font-weight: bold; padding: 6px 18px; min-width: 80px;
            }}
            QPushButton:hover {{ background: {ACCENT_L}; }}
        """)
        open_btn = mb.addButton("Open Folder", QMessageBox.ButtonRole.AcceptRole)
        mb.addButton("OK", QMessageBox.ButtonRole.RejectRole)
        mb.exec()
        if mb.clickedButton() == open_btn:
            folder = str(Path(path).parent)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])


# ── Entry point ────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VideoSlicer")
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(CARD))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(BG))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
