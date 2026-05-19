#!/usr/bin/env python3
"""
DigChur Media —   v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unified launcher for the DIGITAL CHURCH media toolkit.

Tools included:
  ✦  Portrait Split  — face-tracked 9:16 reframe for landscape videos
  ✂  VideoSlicer     — precision video cutter (local + YouTube)

Both tools launch as separate processes so their different UI
frameworks (tkinter vs PyQt6) never conflict.

Requirements:
  pip install PyQt6
  (each sub-tool has its own requirements — see their headers)

Place this file in the same folder as:
  portrait_split_gui.py   (Portrait Split GUI)
  video_slicer.py         (VideoSlicer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import subprocess
from pathlib import Path

from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QRect, QSequentialAnimationGroup,
)
from PyQt6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath,
    QPalette, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget, QFrame, QSpacerItem,
)

# ── Where are the sub-tools? ───────────────────────────────────────
HERE = Path(__file__).parent
PORTRAIT_SCRIPT = HERE / "portrait_split_gui.py"
SLICER_SCRIPT   = HERE / "video_slicer.py"

# ── Palette ────────────────────────────────────────────────────────
BG       = "#07090F"
SURFACE  = "#0C0F1A"
CARD     = "#101422"
BORDER   = "#1C2238"
BORDER2  = "#28304E"

# DC brand colours — gold cross / deep navy
GOLD     = "#C9922A"
GOLD_L   = "#F0B942"
GOLD_D   = "#8A6010"
GOLD_GLW = "#F0B94230"

BLUE     = "#3B6FD4"
BLUE_L   = "#6B9BF5"
TEAL     = "#1CB8A0"
TEAL_L   = "#3DE0C8"
CRIMSON  = "#C43B3B"

TEXT     = "#EEF2FF"
MUTED    = "#5A6480"
MUTED2   = "#8A96B8"
SUCCESS  = "#22C97B"
WARN     = "#E09030"
DANGER   = "#E04040"

FONT_MAIN = "Segoe UI" if sys.platform == "win32" else "Ubuntu"
FONT_MONO = "Consolas"  if sys.platform == "win32" else "Ubuntu Mono"


# ── Tool launcher thread ───────────────────────────────────────────

class LaunchThread(QThread):
    launched = pyqtSignal(str)
    failed   = pyqtSignal(str, str)

    def __init__(self, script: Path, label: str):
        super().__init__()
        self._script = script
        self._label  = label

    def run(self):
        if not self._script.exists():
            self.failed.emit(
                self._label,
                f"Script not found:\n{self._script}\n\n"
                f"Make sure '{self._script.name}' is in the same folder as this launcher."
            )
            return
        try:
            subprocess.Popen(
                [sys.executable, str(self._script)],
                cwd=str(HERE),
            )
            self.launched.emit(self._label)
        except Exception as e:
            self.failed.emit(self._label, str(e))


# ── Animated cross logo ────────────────────────────────────────────

class CrossLogo(QWidget):
    """Draws the DC gold cross with a soft radial glow."""

    def __init__(self, size=72, parent=None):
        super().__init__(parent)
        self._sz   = size
        self._glow = 0.0
        self.setFixedSize(size + 20, size + 20)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer()
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._pulse)
        self._phase = 0.0
        self._timer.start()

    def _pulse(self):
        import math
        self._phase += 0.05
        self._glow = 0.5 + 0.5 * math.sin(self._phase)
        self.update()

    def paintEvent(self, _):
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx  = self.width()  // 2
        cy  = self.height() // 2
        arm = self._sz // 2
        th  = self._sz // 7   # arm thickness

        # radial glow
        alpha = int(60 + 40 * self._glow)
        glow_col = QColor(GOLD_L)
        glow_col.setAlpha(alpha)
        g = QRadialGradient(cx, cy, arm * 1.2)
        g.setColorAt(0, glow_col)
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawEllipse(cx - arm, cy - arm, arm * 2, arm * 2)

        # cross body
        path = QPainterPath()
        path.addRoundedRect(cx - th // 2, cy - arm, th, arm * 2, 4, 4)  # vertical
        path.addRoundedRect(cx - arm, cy - th // 2, arm * 2, th, 4, 4)  # horizontal

        grad = QLinearGradient(cx - arm, cy, cx + arm, cy)
        grad.setColorAt(0,   QColor(GOLD_D))
        grad.setColorAt(0.5, QColor(GOLD_L))
        grad.setColorAt(1,   QColor(GOLD_D))
        p.setBrush(grad)
        p.drawPath(path)
        p.end()


# ── Tool card ──────────────────────────────────────────────────────

class ToolCard(QFrame):
    """
    Clickable card that launches one tool.
    accent   — theme colour for the card border / button
    icon     — big emoji / text symbol
    title    — tool name
    tagline  — one-line description
    bullets  — list of feature strings
    script   — Path to the .py file to run
    """

    clicked = pyqtSignal(Path, str)

    def __init__(self, icon, title, tagline, bullets,
                 script, accent, accent_light, parent=None):
        super().__init__(parent)
        self._accent       = accent
        self._accent_light = accent_light
        self._script       = script
        self._title        = title
        self._hovered      = False

        self.setObjectName("toolcard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self._apply_style(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(14)

        # ── icon ──────────────────────────────────────────────────
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont(FONT_MAIN, 42))
        icon_lbl.setStyleSheet(f"color: {accent_light}; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(icon_lbl)

        # ── title ─────────────────────────────────────────────────
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont(FONT_MAIN, 20, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {TEXT}; background: transparent;")
        lay.addWidget(title_lbl)

        # ── tagline ───────────────────────────────────────────────
        tag_lbl = QLabel(tagline)
        tag_lbl.setFont(QFont(FONT_MAIN, 10))
        tag_lbl.setStyleSheet(f"color: {accent_light}; background: transparent;")
        tag_lbl.setWordWrap(True)
        lay.addWidget(tag_lbl)

        # ── divider ───────────────────────────────────────────────
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {accent}44;")
        lay.addWidget(div)

        # ── bullet features ───────────────────────────────────────
        for b in bullets:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel("◆")
            dot.setFont(QFont(FONT_MONO, 8))
            dot.setStyleSheet(f"color: {accent}; background: transparent;")
            dot.setFixedWidth(14)
            txt = QLabel(b)
            txt.setFont(QFont(FONT_MAIN, 10))
            txt.setStyleSheet(f"color: {MUTED2}; background: transparent;")
            txt.setWordWrap(True)
            row.addWidget(dot)
            row.addWidget(txt, 1)
            lay.addLayout(row)

        lay.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum,
                                      QSizePolicy.Policy.Expanding))

        # ── launch button ─────────────────────────────────────────
        self._btn = QPushButton(f"Open  {title}  →")
        self._btn.setFixedHeight(46)
        self._btn.setFont(QFont(FONT_MAIN, 12, QFont.Weight.Bold))
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self._launch)
        self._style_btn(False)
        lay.addWidget(self._btn)

        # ── script availability warning ───────────────────────────
        if not script.exists():
            warn = QLabel(f"⚠  {script.name} not found in this folder")
            warn.setFont(QFont(FONT_MONO, 8))
            warn.setStyleSheet(f"color: {DANGER}; background: transparent;")
            warn.setWordWrap(True)
            lay.addWidget(warn)

        # drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    def _apply_style(self, hover: bool):
        col   = self._accent_light if hover else self._accent
        bg    = f"{self._accent}18" if hover else CARD
        self.setStyleSheet(f"""
            QFrame#toolcard {{
                background: {bg};
                border: 1.5px solid {col};
                border-radius: 16px;
            }}
        """)

    def _style_btn(self, hover: bool):
        if hover:
            bg, fg, brd = self._accent_light, "#080808", self._accent_light
        else:
            bg, fg, brd = self._accent, TEXT, self._accent
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1.5px solid {brd};
                border-radius: 8px;
                font-family: "{FONT_MAIN}";
                font-size: 12px;
                font-weight: 700;
                padding: 0 18px;
            }}
        """)

    def enterEvent(self, e):
        self._hovered = True
        self._apply_style(True)
        self._style_btn(False)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._apply_style(False)
        self._style_btn(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._launch()
        super().mousePressEvent(e)

    def _launch(self):
        self.clicked.emit(self._script, self._title)


# ── Status bar label ───────────────────────────────────────────────

class StatusBadge(QLabel):
    def set_launching(self, name):
        self.setText(f"⏳  Launching {name} …")
        self.setStyleSheet(f"color: {GOLD_L}; background: transparent;")

    def set_ok(self, name):
        self.setText(f"✔  {name} launched — check your taskbar")
        self.setStyleSheet(f"color: {SUCCESS}; background: transparent;")
        QTimer.singleShot(4000, self.clear_msg)

    def set_error(self, name, msg):
        self.setText(f"✗  Could not launch {name}: {msg}")
        self.setStyleSheet(f"color: {DANGER}; background: transparent;")

    def clear_msg(self):
        self.setText("")


# ── Main Window ────────────────────────────────────────────────────

class DCLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIGCHUR Media Suite")
        self.resize(960, 640)
        self.setMinimumSize(800, 560)
        self._threads = []

        self._build_style()
        self._build()

    def _build_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG}; }}
            QWidget      {{ background: {BG}; }}
            QLabel       {{ color: {TEXT}; background: transparent; }}
            QScrollArea  {{ background: transparent; border: none; }}
        """)
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window,     QColor(BG))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
        self.setPalette(pal)

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(100)
        hdr.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #060810, stop:0.5 #0A0D18, stop:1 #060810
            );
            border-bottom: 1px solid {GOLD_D};
        """)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(36, 0, 36, 0)
        hl.setSpacing(18)

        logo = CrossLogo(56)
        hl.addWidget(logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        app_name = QLabel("DIGCHUR Media")
        app_name.setFont(QFont(FONT_MAIN, 26, QFont.Weight.Bold))
        app_name.setStyleSheet(f"""
            color: {GOLD_L};
            letter-spacing: 4px;
            background: transparent;
        """)
        sub_name = QLabel("DC Media Suite  ·  Portrait Reframe & Video Slicer")
        sub_name.setFont(QFont(FONT_MAIN, 10))
        sub_name.setStyleSheet(f"color: {MUTED2}; letter-spacing: 1px; background: transparent;")
        title_col.addWidget(app_name)
        title_col.addWidget(sub_name)
        hl.addLayout(title_col)
        hl.addStretch()

        badge = QLabel("v1.0")
        badge.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            background: {GOLD_D};
            color: {GOLD_L};
            border-radius: 5px;
            padding: 4px 10px;
        """)
        hl.addWidget(badge)

        main.addWidget(hdr)

        # ── Sub-headline ──────────────────────────────────────────
        intro = QLabel(
            "Select a tool below to launch it. Both can run at the same time."
        )
        intro.setFont(QFont(FONT_MAIN, 10))
        intro.setStyleSheet(f"color: {MUTED}; padding: 14px 36px 0 36px;")
        main.addWidget(intro)

        # ── Cards row ─────────────────────────────────────────────
        cards_wrap = QWidget()
        cl = QHBoxLayout(cards_wrap)
        cl.setContentsMargins(32, 20, 32, 20)
        cl.setSpacing(24)

        portrait_card = ToolCard(
            icon="📐",
            title="Portrait Split",
            tagline="Face-tracked 9:16 reframe — turn landscape sermons & seminars into portrait HD",
            bullets=[
                "OpenCV face detection follows the speaker automatically",
                "Smart EMA smoothing — no jarring camera snaps",
                "Auto-splits into TikTok / Reels / Shorts ready segments",
                "Full 1080×1920 output — not a tiny crop, true HD portrait",
                "Parallel encoding: 4 segments at once for speed",
            ],
            script=PORTRAIT_SCRIPT,
            accent=TEAL,
            accent_light=TEAL_L,
        )
        portrait_card.clicked.connect(self._on_launch)

        slicer_card = ToolCard(
            icon="✂",
            title="VideoSlicer",
            tagline="Precision video cutter — local files or YouTube, zero quality loss",
            bullets=[
                "Paste a YouTube URL or drop a local file",
                "Live video preview with scrub bar — click to set markers",
                "Set Start & End points visually, no manual typing",
                "FFmpeg stream-copy: no re-encoding, no quality loss",
                "YouTube slice via yt-dlp — only downloads the clip you need",
            ],
            script=SLICER_SCRIPT,
            accent=GOLD,
            accent_light=GOLD_L,
        )
        slicer_card.clicked.connect(self._on_launch)

        cl.addWidget(portrait_card)
        cl.addWidget(slicer_card)
        main.addWidget(cards_wrap, 1)

        # ── Footer / status ───────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setStyleSheet(f"""
            background: {SURFACE};
            border-top: 1px solid {BORDER};
        """)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)

        self._status = StatusBadge()
        self._status.setFont(QFont(FONT_MONO, 9))
        fl.addWidget(self._status)
        fl.addStretch()

        credit = QLabel("Built in Uganda by Dihfahsih  ·  DIGCHUR MEDIA")
        credit.setFont(QFont(FONT_MAIN, 8))
        credit.setStyleSheet(f"color: {MUTED}; background: transparent;")
        fl.addWidget(credit)

        main.addWidget(footer)

    def _on_launch(self, script: Path, label: str):
        self._status.set_launching(label)
        t = LaunchThread(script, label)
        t.launched.connect(self._status.set_ok)
        t.failed.connect(self._status.set_error)
        t.start()
        self._threads.append(t)   # keep reference so GC doesn't kill it


# ── Entry point ────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DIGCHUR MEDIA")
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(CARD))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(GOLD))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(BG))
    app.setPalette(pal)

    win = DCLauncher()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
