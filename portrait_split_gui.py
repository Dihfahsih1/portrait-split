#!/usr/bin/env python3
"""
portrait_split_gui.py — Portrait Split v2  (Premium UI)
"""

# ── Windows Crash Prevention ──────────────────────────────────────
import sys
import os
import traceback
import time
from pathlib import Path

# ── Windows DPI awareness — must come before any Tk window ───────
# Without this, Tk apps on high-DPI Windows displays can appear
# blurry, tiny, or positioned off-screen (i.e. invisible to user).
if sys.platform == "win32":
    try:
        import ctypes
        # Per-monitor DPI awareness (best mode on Win 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback: system DPI awareness (Win Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ── Redirect crashes to log file ──────────────────────────────────
CRASH_LOG = Path(__file__).parent / "portrait_split_crash.log"


def log_error(error_msg):
    try:
        with open(CRASH_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n{time.ctime()}\n{error_msg}\n{'='*60}\n")
    except Exception:
        pass


def _show_error_native(title, msg):
    """Show an error box even if Tkinter is unavailable (Windows only)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
            return
        except Exception:
            pass
    # Last resort: print to stderr (visible if launched from a terminal)
    print(f"\n[{title}]\n{msg}", file=sys.stderr)


def global_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    error = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log_error(error)
    detail = (
        f"Application crashed:\n\n{str(exc_value)}\n\n"
        f"Full details written to:\n{CRASH_LOG}"
    )
    # Try Tkinter messagebox first
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Portrait Split Error", detail)
        root.destroy()
    except Exception:
        # Fall back to a Win32 MessageBox so the error is never silent
        _show_error_native("Portrait Split Error", detail)


sys.excepthook = global_exception_handler

# ── Guard: Tkinter must be available ─────────────────────────────
# Tkinter ships with the official Python installer but can be missing
# if Python was installed without the "tcl/tk and IDLE" option, or via
# some minimal distributions. We check early so we can show a useful
# error instead of a silent crash.
try:
    import tkinter as _tk_test
    del _tk_test
except ImportError:
    msg = (
        "Tkinter (Tcl/Tk) is not available in your Python installation.\n\n"
        "Fix on Windows:\n"
        "  1. Open 'Add or Remove Programs'\n"
        "  2. Find Python, click 'Modify'\n"
        "  3. Enable the 'tcl/tk and IDLE' optional feature\n\n"
        "Or reinstall Python from https://python.org and tick\n"
        "'tcl/tk and IDLE' during installation."
    )
    log_error(f"ImportError: tkinter not available\n{msg}")
    _show_error_native("Portrait Split — Missing Tkinter", msg)
    sys.exit(1)

# ── Core engine must exist ────────────────────────────────────────
CORE_SCRIPT = Path(__file__).parent / "portrait_split.py"
if not CORE_SCRIPT.exists():
    msg = (
        f"Core engine not found:\n{CORE_SCRIPT}\n\n"
        "Make sure portrait_split.py is in the same folder as this file."
    )
    log_error(msg)
    _show_error_native("Portrait Split — Missing Engine", msg)
    sys.exit(1)

# ── Normal imports ────────────────────────────────────────────────
import multiprocessing as mp
import subprocess
import threading
import queue
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ── Palette ───────────────────────────────────────────────────────
C = {
    "bg":        "#080810",
    "bg2":       "#0E0E1A",
    "surface":   "#12121E",
    "surface2":  "#1A1A2E",
    "surface3":  "#22223A",
    "border":    "#2E2E4A",
    "border2":   "#3A3A5C",
    "purple":    "#7C6FFF",
    "purple2":   "#A99CFF",
    "pink":      "#FF6B9D",
    "pink2":     "#FF8FB3",
    "cyan":      "#00D4FF",
    "green":     "#00E5A0",
    "yellow":    "#FFB800",
    "text":      "#F4F4FF",
    "text2":     "#9090B8",
    "text3":     "#50507A",
    "text4":     "#30304A",
}

FONTS = {
    "display":  ("Sans", 20, "bold"),
    "title":    ("Sans", 13, "bold"),
    "subtitle": ("Sans", 10, "bold"),
    "body":     ("Sans", 9),
    "small":    ("Sans", 8),
    "mono":     ("Monospace", 9),
    "mono_sm":  ("Monospace", 8),
}


# ══════════════════════════════════════════════════════════════════
# Custom Widgets
# ══════════════════════════════════════════════════════════════════

class GlowButton(tk.Canvas):
    """Pill button with animated glow on hover."""

    def __init__(self, parent, text, command=None,
                 color=C["purple"], width=200, height=46, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=C["bg"], highlightthickness=0,
                         cursor="hand2")
        self._text    = text
        self._cmd     = command
        self._color   = color
        self._bw      = width
        self._bh      = height
        self._alpha   = 0.0
        self._anim_id = None
        self._enabled = True

        self.bind("<Enter>",     self._hover_in)
        self.bind("<Leave>",     self._hover_out)
        self.bind("<Button-1>",  self._click)
        self.bind("<Configure>", lambda e: self._paint())
        self._paint()

    def _hex_blend(self, c1, c2, t):
        def h(c): return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
        r1, g1, b1 = h(c1);  r2, g2, b2 = h(c2)
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _paint(self):
        self.delete("all")
        w, h, r = self._bw, self._bh, self._bh // 2
        t = self._alpha

        if t > 0:
            for i in range(8, 0, -1):
                expand = i * 2 * t
                glow_c = self._hex_blend(C["bg"], self._color,
                                         t * 0.12 * (9-i)/8)
                self._pill(expand, expand, w-expand, h-expand,
                           r + expand//2, glow_c)

        body_c = self._hex_blend(self._color,
                                 self._hex_blend(self._color, "#FFFFFF", 0.15),
                                 t * 0.3)
        self._pill(0, 0, w, h, r, body_c)

        shine_c = self._hex_blend(body_c, "#FFFFFF", 0.18 + t*0.1)
        self._pill(2, 2, w-2, h//2, r-2, shine_c)

        lc = C["text"] if self._enabled else C["text3"]
        self.create_text(w//2, h//2, text=self._text,
                         fill=lc, font=FONTS["subtitle"])

    def _pill(self, x1, y1, x2, y2, r, color):
        r = max(1, int(r))
        self.create_polygon(
            x1+r, y1,   x2-r, y1,
            x2,   y1,   x2,   y1+r,
            x2,   y2-r, x2,   y2,
            x2-r, y2,   x1+r, y2,
            x1,   y2,   x1,   y2-r,
            x1,   y1+r, x1,   y1,
            smooth=True, fill=color, outline="",
        )

    def _hover_in(self, _):
        self._animate_to(1.0)

    def _hover_out(self, _):
        self._animate_to(0.0)

    def _animate_to(self, target):
        if self._anim_id:
            self.after_cancel(self._anim_id)
        def step():
            diff = target - self._alpha
            if abs(diff) < 0.03:
                self._alpha = target
                self._paint()
                return
            self._alpha += diff * 0.25
            self._paint()
            self._anim_id = self.after(16, step)
        step()

    def _click(self, _):
        if self._cmd and self._enabled:
            self._cmd()

    def set_enabled(self, val):
        self._enabled = val
        self._cmd = self._cmd if val else None
        self._paint()


class GhostButton(tk.Canvas):
    """Outlined ghost button."""

    def __init__(self, parent, text, command=None,
                 width=120, height=34, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=C["bg2"], highlightthickness=0, cursor="hand2")
        self._text  = text
        self._cmd   = command
        self._bw    = width
        self._bh    = height
        self._hover = False
        self.bind("<Enter>",     lambda e: self._set(True))
        self.bind("<Leave>",     lambda e: self._set(False))
        self.bind("<Button-1>",  lambda e: self._cmd() if self._cmd else None)
        self.bind("<Configure>", lambda e: self._paint())
        self._paint()

    def _set(self, h):
        self._hover = h; self._paint()

    def _paint(self):
        self.delete("all")
        w, h, r = self._bw, self._bh, self._bh // 2
        bc = C["border2"] if self._hover else C["border"]
        tc = C["text2"]   if self._hover else C["text3"]
        self.create_polygon(
            r, 0,   w-r, 0,
            w, 0,   w, r,
            w, h-r, w, h,
            w-r, h, r, h,
            0, h,   0, h-r,
            0, r,   0, 0,
            smooth=True,
            fill=C["surface3"] if self._hover else C["surface2"],
            outline=bc, width=1,
        )
        self.create_text(w//2, h//2, text=self._text,
                         fill=tc, font=FONTS["small"])


class DropZone(tk.Frame):
    """Animated file / folder pick zone."""

    def __init__(self, parent, var, label, hint, mode="file",
                 accent=C["purple"], **kw):
        super().__init__(parent, bg=C["surface2"],
                         cursor="hand2", **kw)
        self._var    = var
        self._mode   = mode
        self._accent = accent
        self._picked = False

        self.configure(highlightthickness=1,
                       highlightbackground=C["border"])

        self._icon = tk.Label(self, text="⬆", font=("Sans", 22),
                              bg=C["surface2"], fg=accent)
        self._icon.pack(pady=(16, 4))

        self._lbl = tk.Label(self, text=label,
                             font=FONTS["subtitle"],
                             bg=C["surface2"], fg=C["text"])
        self._lbl.pack()

        self._hint = tk.Label(self, text=hint,
                              font=FONTS["small"],
                              bg=C["surface2"], fg=C["text3"])
        self._hint.pack(pady=(2, 16))

        for w in (self, self._icon, self._lbl, self._hint):
            w.bind("<Button-1>", self._pick)
            w.bind("<Enter>",    self._hover_in)
            w.bind("<Leave>",    self._hover_out)

    def _hover_in(self, _):
        self.configure(highlightbackground=self._accent,
                       bg=C["surface3"])
        for w in (self._icon, self._lbl, self._hint):
            w.configure(bg=C["surface3"])

    def _hover_out(self, _):
        bc = self._accent if self._picked else C["border"]
        self.configure(highlightbackground=bc, bg=C["surface2"])
        for w in (self._icon, self._lbl, self._hint):
            w.configure(bg=C["surface2"])

    def _pick(self, _=None):
        if self._mode == "file":
            p = filedialog.askopenfilename(
                title="Select video",
                filetypes=[("MP4","*.mp4"), ("All","*.*")])
        else:
            p = filedialog.askdirectory(title="Select output folder")
        if p:
            self._var.set(p)
            self._picked = True
            short = Path(p).name
            if len(short) > 28:
                short = "…" + short[-26:]
            self._lbl.configure(text=short, fg=C["green"])
            self._hint.configure(text="Click to change",
                                 fg=C["text3"])
            self._icon.configure(text="✓", fg=C["green"])
            self.configure(highlightbackground=C["green"])


class StatCard(tk.Frame):
    """Single metric card."""

    def __init__(self, parent, label, icon, color, **kw):
        super().__init__(parent, bg=C["surface2"],
                         highlightthickness=1,
                         highlightbackground=C["border"], **kw)
        tk.Label(self, text=icon, font=("Sans", 16),
                 bg=C["surface2"], fg=color).pack(pady=(12, 2))
        self._val = tk.Label(self, text="—",
                             font=("Monospace", 13, "bold"),
                             bg=C["surface2"], fg=C["text"])
        self._val.pack()
        tk.Label(self, text=label, font=FONTS["small"],
                 bg=C["surface2"], fg=C["text3"]).pack(pady=(2, 12))

    def set(self, v):
        self._val.configure(text=v)


class SectionCard(tk.Frame):
    """Titled card panel."""

    def __init__(self, parent, title, icon, accent=C["purple"], **kw):
        super().__init__(parent, bg=C["surface"],
                         highlightthickness=1,
                         highlightbackground=C["border"], **kw)
        hdr = tk.Frame(self, bg=C["surface2"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=icon, font=("Sans", 11),
                 bg=C["surface2"], fg=accent).pack(side="left",
                                                    padx=(14,4), pady=10)
        tk.Label(hdr, text=title, font=FONTS["subtitle"],
                 bg=C["surface2"], fg=accent).pack(side="left", pady=10)
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")
        self.body = tk.Frame(self, bg=C["surface"])
        self.body.pack(fill="both", expand=True, padx=14, pady=10)


class SettingRow(tk.Frame):
    """Label + spinbox row."""

    def __init__(self, parent, label, var, from_, to, tip="", color=None, **kw):
        super().__init__(parent, bg=C["surface"])
        tk.Label(self, text=label, font=FONTS["body"],
                 bg=C["surface"], fg=C["text2"]).pack(side="left")
        sb = tk.Spinbox(self, from_=from_, to=to, textvariable=var,
                        width=6, font=FONTS["mono"],
                        bg=C["surface3"], fg=C["text"],
                        buttonbackground=C["border2"],
                        insertbackground=C["text"],
                        relief="flat", bd=4,
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        highlightcolor=C["purple"])
        sb.pack(side="right")
        if tip:
            tk.Label(self, text=tip, font=FONTS["small"],
                     bg=C["surface"], fg=C["text4"]).pack(
                         side="left", padx=(6,0))


class SmartSlider(tk.Frame):
    """Slider with animated value pill."""

    def __init__(self, parent, label, var, from_, to,
                 resolution=0.05, fmt="{:.2f}", color=C["purple"], **kw):
        super().__init__(parent, bg=C["surface"])
        self._fmt = fmt
        self._var = var
        self._color = color

        top = tk.Frame(self, bg=C["surface"])
        top.pack(fill="x")
        tk.Label(top, text=label, font=FONTS["body"],
                 bg=C["surface"], fg=C["text2"]).pack(side="left")

        self._pill = tk.Label(top, text=fmt.format(var.get()),
                              font=("Monospace", 8, "bold"),
                              bg=color, fg=C["text"],
                              padx=8, pady=2)
        self._pill.pack(side="right")

        style = ttk.Style()
        style.configure("PS.Horizontal.TScale",
                        background=C["surface"],
                        troughcolor=C["surface3"],
                        sliderlength=20,
                        sliderrelief="flat")

        ttk.Scale(self, from_=from_, to=to, variable=var,
                  orient="horizontal",
                  style="PS.Horizontal.TScale",
                  command=self._update).pack(fill="x", pady=(4,0))

    def _update(self, v):
        self._pill.configure(text=self._fmt.format(float(v)))


class PulsingDot(tk.Canvas):
    """Animated status dot."""

    def __init__(self, parent, **kw):
        super().__init__(parent, width=14, height=14,
                         bg=C["surface"], highlightthickness=0)
        self._color  = C["text3"]
        self._phase  = 0.0
        self._anim   = False
        self._job    = None
        self._draw()

    def _draw(self):
        self.delete("all")
        r = 5
        if self._anim:
            pulse = 0.5 + 0.5 * math.sin(self._phase)
            outer = int(r + pulse * 3)
            self.create_oval(7-outer, 7-outer, 7+outer, 7+outer,
                             fill="", outline=self._color,
                             width=1)
        self.create_oval(7-r, 7-r, 7+r, 7+r,
                         fill=self._color, outline="")

    def _tick(self):
        self._phase += 0.2
        self._draw()
        if self._anim:
            self._job = self.after(50, self._tick)

    def set_idle(self):
        self._anim = False; self._color = C["text3"]
        if self._job: self.after_cancel(self._job)
        self._draw()

    def set_active(self):
        self._anim = True; self._color = C["purple"]
        self._tick()

    def set_done(self):
        self._anim = False; self._color = C["green"]
        if self._job: self.after_cancel(self._job)
        self._draw()

    def set_error(self):
        self._anim = False; self._color = C["pink"]
        if self._job: self.after_cancel(self._job)
        self._draw()


class LogBox(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["bg2"])
        self.text = tk.Text(
            self, font=FONTS["mono_sm"],
            bg=C["bg2"], fg=C["text2"],
            insertbackground=C["text"],
            selectbackground=C["purple"],
            relief="flat", bd=0,
            state="disabled", wrap="word",
            spacing1=3, spacing3=3,
        )
        sb = tk.Scrollbar(self, command=self.text.yview,
                          width=6, relief="flat",
                          bg=C["surface"], troughcolor=C["bg2"])
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True, padx=4)
        self.text.configure(yscrollcommand=sb.set)
        self.text.tag_config("ok",   foreground=C["green"])
        self.text.tag_config("warn", foreground=C["yellow"])
        self.text.tag_config("err",  foreground=C["pink"])
        self.text.tag_config("head", foreground=C["purple"],
                             font=("Monospace", 9, "bold"))
        self.text.tag_config("dim",  foreground=C["text3"])

    def append(self, msg, tag=None):
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", tag or "")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


# ══════════════════════════════════════════════════════════════════
# Main App
# ══════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Portrait Split  v2")
        self.configure(bg=C["bg"])
        self.geometry("980x700")
        self.minsize(880, 620)

        self._running  = False
        self._proc     = None
        self._log_q    = queue.Queue()
        self._parts_done = 0

        self._build()
        self._poll()

    # ── Layout ───────────────────────────────────────────────────

    def _build(self):
        left = tk.Frame(self, bg=C["surface"], width=270)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_sidebar(left)

        right = tk.Frame(self, bg=C["bg"])
        right.pack(side="right", fill="both", expand=True)
        self._build_topbar(right)
        self._build_content(right)

    def _build_sidebar(self, parent):
        # Logo
        logo = tk.Frame(parent, bg=C["surface"])
        logo.pack(fill="x", padx=20, pady=(28, 0))

        tk.Label(logo, text="✦", font=("Sans", 30),
                 bg=C["surface"], fg=C["purple"]).pack(anchor="w")

        tk.Label(logo, text="Portrait Split",
                 font=("Sans", 17, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(anchor="w", pady=(4,0))

        ver_row = tk.Frame(logo, bg=C["surface"])
        ver_row.pack(anchor="w", pady=(2,0))
        tk.Label(ver_row, text="v2", font=FONTS["small"],
                 bg=C["purple"], fg=C["text"],
                 padx=6, pady=1).pack(side="left")
        tk.Label(ver_row, text="  by AutoPro UG",
                 font=FONTS["small"],
                 bg=C["surface"], fg=C["text3"]).pack(side="left")

        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=20, pady=22)

        self._label(parent, "INPUT VIDEO", icon="▶")
        self.v_input = tk.StringVar()
        DropZone(parent, self.v_input,
                 "Select source MP4",
                 "Click to browse",
                 mode="file", accent=C["purple"]).pack(
                     fill="x", padx=16, pady=(4,14))

        self._label(parent, "OUTPUT FOLDER", icon="📁")
        self.v_output = tk.StringVar()
        DropZone(parent, self.v_output,
                 "Select output folder",
                 "Click to browse",
                 mode="dir", accent=C["cyan"]).pack(
                     fill="x", padx=16, pady=(4,14))

        self._label(parent, "BASE FILENAME  (optional)", icon="✏")
        self.v_name = tk.StringVar()
        entry_frame = tk.Frame(parent, bg=C["surface3"],
                               highlightthickness=1,
                               highlightbackground=C["border"])
        entry_frame.pack(fill="x", padx=16, pady=(4,4))
        tk.Entry(entry_frame, textvariable=self.v_name,
                 font=FONTS["mono_sm"],
                 bg=C["surface3"], fg=C["text"],
                 insertbackground=C["text"],
                 relief="flat", bd=6).pack(fill="x")
        tk.Label(parent, text="e.g.  Speaker — Event 2026",
                 font=FONTS["small"],
                 bg=C["surface"], fg=C["text4"]).pack(
                     anchor="w", padx=18, pady=(0,4))

        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=20, pady=18)

        self.btn_start = GlowButton(
            parent, "▶   Start Processing",
            command=self._start,
            color=C["purple"], width=238, height=48)
        self.btn_start.pack(padx=16, pady=(0,10))

        self.btn_stop = GlowButton(
            parent, "⏹   Stop",
            command=self._stop,
            color=C["pink"], width=238, height=38)
        self.btn_stop.pack(padx=16)

        status_row = tk.Frame(parent, bg=C["surface"])
        status_row.pack(anchor="w", padx=18, pady=16)

        self._dot = PulsingDot(status_row)
        self._dot.pack(side="left", padx=(0,8))

        self._status_lbl = tk.Label(
            status_row, text="Ready",
            font=FONTS["small"],
            bg=C["surface"], fg=C["text2"])
        self._status_lbl.pack(side="left")

    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=C["bg2"], height=44)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self._tabs = {}
        for key, label in [("settings", "⚙  Settings"), ("log", "📋  Log")]:
            btn = tk.Button(
                bar, text=label,
                font=FONTS["small"],
                bg=C["surface2"], fg=C["text2"],
                activebackground=C["purple"], activeforeground=C["text"],
                relief="flat", bd=0, padx=16,
                command=lambda k=key: self._switch(k))
            btn.pack(side="left", fill="y")
            self._tabs[key] = btn

        self._active_tab = "settings"
        self._tabs["settings"].configure(bg=C["purple"])

    def _build_content(self, parent):
        container = tk.Frame(parent, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=16, pady=16)

        self._settings_frame = self._build_settings(container)
        self._log_frame      = self._build_log(container)

        self._settings_frame.pack(fill="both", expand=True)

    def _build_settings(self, parent):
        outer = tk.Frame(parent, bg=C["bg"])

        # ── Row 1: Encoding cards ────────────────────────────────
        row1 = tk.Frame(outer, bg=C["bg"])
        row1.pack(fill="x", pady=(0, 12))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)

        # Card: Segments
        c1 = SectionCard(row1, "Segments", "✂", accent=C["purple"])
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.v_segment  = tk.IntVar(value=200)
        self.v_parallel = tk.IntVar(value=4)
        SettingRow(c1.body, "Segment length (s)",
                   self.v_segment, 30, 3600).pack(fill="x", pady=4)
        SettingRow(c1.body, "Parallel segments",
                   self.v_parallel, 1, 16).pack(fill="x", pady=4)

        # Card: Encoding
        c2 = SectionCard(row1, "Encoding", "🎬", accent=C["cyan"])
        c2.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.v_crf    = tk.IntVar(value=18)
        self.v_preset = tk.StringVar(value="fast")

        SettingRow(c2.body, "CRF quality (0–51)",
                   self.v_crf, 0, 51).pack(fill="x", pady=4)

        tk.Label(c2.body, text="Encoding preset",
                 font=FONTS["body"],
                 bg=C["surface"], fg=C["text2"]).pack(anchor="w")
        presets = ["ultrafast","superfast","veryfast",
                   "faster","fast","medium","slow","slower"]
        pm = tk.Frame(c2.body, bg=C["surface"])
        pm.pack(fill="x", pady=(2, 0))
        for p in presets:
            tk.Radiobutton(
                pm, text=p, variable=self.v_preset, value=p,
                font=FONTS["small"],
                bg=C["surface"], fg=C["text3"],
                selectcolor=C["purple"],
                activebackground=C["surface"],
                relief="flat").pack(side="left")

        # ── Row 2: Tracking + Stats ──────────────────────────────
        row2 = tk.Frame(outer, bg=C["bg"])
        row2.pack(fill="both", expand=True)
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        # Card: Tracking
        c3 = SectionCard(row2, "Face Tracking", "🎯", accent=C["pink"])
        c3.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.v_smooth   = tk.DoubleVar(value=0.3)
        self.v_max_jump = tk.IntVar(value=400)
        self.v_max_drift = tk.IntVar(value=6)

        SmartSlider(c3.body, "Tracking speed",
                    self.v_smooth, 0.05, 1.0,
                    color=C["pink"]).pack(fill="x", pady=(0,8))

        tk.Label(c3.body,
                 text="0.1 = cinematic drift   ·   1.0 = instant snap",
                 font=FONTS["small"],
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w")

        tk.Frame(c3.body, bg=C["border"], height=1).pack(
            fill="x", pady=8)

        SettingRow(c3.body, "Max jump (px)",
                   self.v_max_jump, 50, 960,
                   tip="ignore far faces").pack(fill="x", pady=4)
        SettingRow(c3.body, "Max drift (px/frame)",
                   self.v_max_drift, 1, 30,
                   tip="pan speed cap").pack(fill="x", pady=4)

        # Card: Stats
        c4 = SectionCard(row2, "Session Stats", "📊", accent=C["green"])
        c4.grid(row=0, column=1, sticky="nsew", padx=(8,0))

        stat_grid = tk.Frame(c4.body, bg=C["surface"])
        stat_grid.pack(fill="x")
        stat_grid.columnconfigure(0, weight=1)
        stat_grid.columnconfigure(1, weight=1)
        stat_grid.columnconfigure(2, weight=1)

        self._sc_parts = StatCard(stat_grid, "Parts done", "✅", C["green"])
        self._sc_parts.grid(row=0, column=0, padx=(0,4), sticky="nsew")

        self._sc_speed = StatCard(stat_grid, "Speed", "⚡", C["yellow"])
        self._sc_speed.grid(row=0, column=1, padx=4, sticky="nsew")

        self._sc_eta = StatCard(stat_grid, "ETA", "⏱", C["cyan"])
        self._sc_eta.grid(row=0, column=2, padx=(4,0), sticky="nsew")

        pb_outer = tk.Frame(c4.body, bg=C["surface3"],
                            highlightthickness=1,
                            highlightbackground=C["border"])
        pb_outer.pack(fill="x", pady=(12,4))

        self._progress = ttk.Progressbar(
            pb_outer, mode="indeterminate", length=300)
        self._progress.pack(fill="x", padx=2, pady=2)

        self._progress_lbl = tk.Label(
            c4.body, text="Waiting …",
            font=FONTS["small"],
            bg=C["surface"], fg=C["text3"])
        self._progress_lbl.pack(anchor="w")

        return outer

    def _build_log(self, parent):
        frame = tk.Frame(parent, bg=C["bg"])

        hdr = tk.Frame(frame, bg=C["bg"])
        hdr.pack(fill="x", pady=(0,8))
        tk.Label(hdr, text="📋  Live Output",
                 font=FONTS["subtitle"],
                 bg=C["bg"], fg=C["text2"]).pack(side="left")

        GhostButton(hdr, "🗑  Clear log",
                    command=lambda: self._logbox.clear(),
                    width=100, height=28).pack(side="right")

        self._logbox = LogBox(frame)
        self._logbox.pack(fill="both", expand=True)
        return frame

    # ── Helpers ──────────────────────────────────────────────────

    def _label(self, parent, text, icon=""):
        row = tk.Frame(parent, bg=C["surface"])
        row.pack(fill="x", padx=18, pady=(0,2))
        tk.Label(row, text=f"{icon}  {text}" if icon else text,
                 font=("Sans", 7, "bold"),
                 bg=C["surface"], fg=C["text3"]).pack(side="left")

    def _switch(self, tab):
        self._active_tab = tab
        for k, btn in self._tabs.items():
            btn.configure(bg=C["purple"] if k==tab else C["surface2"])
        self._settings_frame.pack_forget()
        self._log_frame.pack_forget()
        if tab == "settings":
            self._settings_frame.pack(fill="both", expand=True)
        else:
            self._log_frame.pack(fill="both", expand=True)

    def _set_status(self, text, state="idle"):
        self._status_lbl.configure(text=text)
        if state == "active": self._dot.set_active()
        elif state == "done": self._dot.set_done()
        elif state == "error": self._dot.set_error()
        else: self._dot.set_idle()

    # ── Actions ──────────────────────────────────────────────────

    def _start(self):
        src = self.v_input.get().strip()
        if not src or not Path(src).is_file():
            messagebox.showerror("No input",
                                 "Please select a valid MP4 file.")
            return

        out = self.v_output.get().strip()
        if not out:
            out = str(Path(src).parent / (Path(src).stem + "_portrait"))
            self.v_output.set(out)

        name   = self.v_name.get().strip() or Path(src).stem
        seg    = self.v_segment.get()
        par    = self.v_parallel.get()
        crf    = self.v_crf.get()
        smooth = self.v_smooth.get()
        preset = self.v_preset.get()
        jump   = self.v_max_jump.get()
        drift  = self.v_max_drift.get()

        self._running    = True
        self._parts_done = 0
        self._sc_parts.set("0")
        self._sc_speed.set("—")
        self._sc_eta.set("—")
        self._set_status("Processing …", "active")
        self._progress.start(10)
        self._progress_lbl.configure(text="Running …")
        self._switch("log")
        self._logbox.clear()
        self._logbox.append("▶  Portrait Split v2  —  Starting", "head")
        self._logbox.append(f"   {Path(src).name}", "dim")
        self._logbox.append(f"   → {out}", "dim")
        self._logbox.append("")

        threading.Thread(
            target=self._worker,
            args=(src, out, name, seg, smooth,
                  crf, preset, par, jump, drift),
            daemon=True).start()

    def _worker(self, src, out, name, seg, smooth,
                crf, preset, par, jump, drift):
        script = Path(__file__).parent / "portrait_split.py"

        # On Windows, always use python.exe (not pythonw.exe) for the
        # worker subprocess so its stdout can be piped reliably.
        # pythonw.exe has no console and may buffer stdout aggressively,
        # causing the live-log reader here to stall indefinitely.
        if sys.platform == "win32":
            python_exe = Path(sys.executable)
            # If we were launched via pythonw.exe, swap to python.exe
            if python_exe.stem.lower() == "pythonw":
                alt = python_exe.parent / "python.exe"
                python_exe = alt if alt.exists() else python_exe
            python_exe = str(python_exe)
        else:
            python_exe = sys.executable

        cmd = [
            python_exe, str(script),
            "-i", src, "-o", out, "-n", name,
            "-s", str(seg),
            "--smooth",    str(round(smooth, 3)),
            "--crf",       str(crf),
            "--preset",    preset,
            "--parallel",  str(par),
            "--max-jump",  str(jump),
            "--max-drift", str(drift),
        ]
        try:
            # On Windows: CREATE_NO_WINDOW prevents a console flash,
            # but still allows stdout piping.
            kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._proc = subprocess.Popen(cmd, **kwargs)
            for line in self._proc.stdout:
                if not self._running:
                    self._proc.terminate(); break
                line = line.rstrip()
                tag = ("ok"   if "✅" in line or "Done" in line
                       else "warn" if "warn" in line.lower()
                       else "err"  if "error" in line.lower()
                       else "dim"  if line.strip().startswith("─")
                       else None)
                self._log_q.put(("log", line, tag))
                if "complete" in line.lower():
                    self._log_q.put(("parts", None, None))
                if "fps" in line and "frame" in line:
                    for tok in line.split():
                        if tok.isdigit() and int(tok) > 5:
                            self._log_q.put(("speed", tok+" fps", None))
                            break
            self._proc.wait()
            if self._running:
                self._log_q.put(("done", "", None))
        except Exception as e:
            self._log_q.put(("log", f"ERROR: {e}", "err"))
            self._log_q.put(("done", "", None))

    def _stop(self):
        self._running = False
        if self._proc:
            try: self._proc.terminate()
            except: pass
        self._logbox.append("\n⏹  Stopped by user.", "warn")
        self._reset()

    def _poll(self):
        try:
            while True:
                item = self._log_q.get_nowait()
                kind, val, _ = item
                if kind == "log":
                    self._logbox.append(val, item[2])
                elif kind == "parts":
                    self._parts_done += 1
                    self._sc_parts.set(str(self._parts_done))
                elif kind == "speed":
                    self._sc_speed.set(val)
                elif kind == "done":
                    self._logbox.append(
                        "\n🎉  All parts complete!", "ok")
                    self._set_status("Done!", "done")
                    self._progress_lbl.configure(
                        text="Complete ✓")
                    self._reset(keep_status=True)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _reset(self, keep_status=False):
        self._running = False
        self._progress.stop()
        if not keep_status:
            self._set_status("Ready", "idle")
            self._progress_lbl.configure(text="Waiting …")


def main():
    # freeze_support() must be the very first call in __main__ on Windows
    # to prevent recursive spawning when multiprocessing creates child processes.
    mp.freeze_support()

    # 'spawn' is already the default on Windows, but being explicit ensures
    # the same behaviour if someone runs this on Linux/macOS.
    # force=True lets us call this even if it was already set somewhere else.
    mp.set_start_method("spawn", force=True)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
