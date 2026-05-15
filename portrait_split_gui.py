#!/usr/bin/env python3
"""
portrait_split_gui.py — Portrait Split v2
Premium desktop GUI with modern design.
"""

import multiprocessing as mp
import subprocess
import sys
import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont


# ── Design tokens ─────────────────────────────────────────────────
C = {
    "bg":        "#0D0D12",
    "surface":   "#13131A",
    "surface2":  "#1C1C28",
    "border":    "#2A2A3C",
    "primary":   "#6C63FF",
    "primary2":  "#8B83FF",
    "accent":    "#FF6584",
    "success":   "#43D9AD",
    "warning":   "#FFB347",
    "text":      "#F0F0FF",
    "text2":     "#8888AA",
    "text3":     "#55556A",
}


class RoundedFrame(tk.Canvas):
    """Canvas-based rounded-corner container."""
    def __init__(self, parent, radius=12, bg=C["surface"], border=C["border"],
                 **kwargs):
        super().__init__(parent, bg=C["bg"], highlightthickness=0, **kwargs)
        self._radius = radius
        self._bg     = bg
        self._border = border
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _=None):
        self.delete("all")
        w, h, r = self.winfo_width(), self.winfo_height(), self._radius
        if w < 2 or h < 2:
            return
        # border
        self._rounded_rect(1, 1, w-2, h-2, r, self._border)
        # fill
        self._rounded_rect(2, 2, w-3, h-3, r-1, self._bg)

    def _rounded_rect(self, x1, y1, x2, y2, r, color):
        self.create_polygon(
            x1+r, y1,  x2-r, y1,
            x2, y1,    x2, y1+r,
            x2, y2-r,  x2, y2,
            x2-r, y2,  x1+r, y2,
            x1, y2,    x1, y2-r,
            x1, y1+r,  x1, y1,
            smooth=True, fill=color, outline="",
        )


class ModernButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, style="primary",
                 width=160, height=42, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=C["bg"], highlightthickness=0, cursor="hand2")
        self._text    = text
        self._command = command
        self._style   = style
        self._w       = width
        self._h       = height
        self._hover   = False

        colors = {
            "primary": (C["primary"], C["primary2"]),
            "danger":  (C["accent"],  "#FF8096"),
            "ghost":   (C["surface2"], C["border"]),
        }
        self._c_normal, self._c_hover = colors.get(style, colors["primary"])

        self.bind("<Enter>",        self._on_enter)
        self.bind("<Leave>",        self._on_leave)
        self.bind("<Button-1>",     self._on_click)
        self.bind("<Configure>",    self._draw)
        self._draw()

    def _draw(self, _=None):
        self.delete("all")
        w, h, r = self._w, self._h, 10
        c = self._c_hover if self._hover else self._c_normal

        # glow effect on primary
        if self._style == "primary" and self._hover:
            self.create_oval(w//2-50, h//2-20, w//2+50, h//2+20,
                             fill="", outline=C["primary"], width=8)

        # pill background
        self.create_polygon(
            r, 0,  w-r, 0,
            w, 0,  w, r,
            w, h-r, w, h,
            w-r, h, r, h,
            0, h,  0, h-r,
            0, r,  0, 0,
            smooth=True, fill=c, outline="",
        )
        fg = C["text"] if self._style != "ghost" else C["text2"]
        self.create_text(w//2, h//2, text=self._text,
                         fill=fg, font=("SF Pro Display", 11, "bold")
                         if sys.platform == "darwin"
                         else ("Sans", 10, "bold"))

    def _on_enter(self, _):
        self._hover = True;  self._draw()

    def _on_leave(self, _):
        self._hover = False; self._draw()

    def _on_click(self, _):
        if self._command:
            self._command()

    def configure_state(self, state):
        self._command = None if state == "disabled" else self._command


class Slider(tk.Frame):
    """Labelled slider with live value display."""
    def __init__(self, parent, label, var, from_, to, resolution=0.05,
                 fmt="{:.2f}", **kwargs):
        super().__init__(parent, bg=C["bg"])
        self._fmt = fmt
        tk.Label(self, text=label, font=("Sans", 9),
                 bg=C["bg"], fg=C["text2"]).pack(anchor="w")
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x")
        self._lbl = tk.Label(row, text=fmt.format(var.get()),
                             font=("Monospace", 9, "bold"),
                             bg=C["bg"], fg=C["primary"], width=5)
        self._lbl.pack(side="right")
        s = ttk.Scale(row, from_=from_, to=to, variable=var,
                      orient="horizontal", command=self._update)
        s.pack(side="left", fill="x", expand=True, padx=(0,6))
        self._var = var

    def _update(self, v):
        self._lbl.configure(text=self._fmt.format(float(v)))


class LogBox(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg"])
        self.text = tk.Text(
            self, font=("Monospace", 8),
            bg=C["surface"], fg=C["text2"],
            insertbackground=C["text"],
            selectbackground=C["primary"],
            relief="flat", bd=0,
            state="disabled", wrap="word",
            spacing1=2, spacing3=2,
        )
        sb = tk.Scrollbar(self, command=self.text.yview,
                          bg=C["surface"], troughcolor=C["bg"],
                          width=8, relief="flat")
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.configure(yscrollcommand=sb.set)
        self.text.tag_config("ok",   foreground=C["success"])
        self.text.tag_config("warn", foreground=C["warning"])
        self.text.tag_config("err",  foreground=C["accent"])
        self.text.tag_config("head", foreground=C["primary"],
                             font=("Monospace", 8, "bold"))

    def append(self, msg, tag=None):
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", tag or "")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class FileDropZone(tk.Frame):
    """Clickable file pick area."""
    def __init__(self, parent, var, label, mode="file", **kwargs):
        super().__init__(parent, bg=C["surface2"],
                         cursor="hand2", **kwargs)
        self._var  = var
        self._mode = mode
        self._build(label)
        self.bind("<Button-1>", self._pick)
        for w in self.winfo_children():
            w.bind("<Button-1>", self._pick)

    def _build(self, label):
        tk.Label(self, text="📂", font=("Sans", 18),
                 bg=C["surface2"], fg=C["primary"]).pack(pady=(14,2))
        tk.Label(self, text=label, font=("Sans", 9, "bold"),
                 bg=C["surface2"], fg=C["text"]).pack()
        self._sub = tk.Label(self, text="Click to browse",
                             font=("Sans", 8),
                             bg=C["surface2"], fg=C["text3"])
        self._sub.pack(pady=(2,14))

    def _pick(self, _=None):
        if self._mode == "file":
            p = filedialog.askopenfilename(
                title="Select video",
                filetypes=[("MP4 files","*.mp4"),("All files","*.*")])
        else:
            p = filedialog.askdirectory(title="Select output folder")
        if p:
            self._var.set(p)
            short = Path(p).name
            self._sub.configure(text=short, fg=C["success"])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Portrait Split  v2")
        self.configure(bg=C["bg"])
        self.geometry("900x680")
        self.minsize(820, 600)

        self._running = False
        self._proc    = None
        self._log_q   = queue.Queue()

        self._style_ttk()
        self._build()
        self._poll_log()

    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TScale",
                    background=C["bg"],
                    troughcolor=C["surface2"],
                    sliderlength=18,
                    sliderrelief="flat")
        s.configure("TCombobox",
                    fieldbackground=C["surface2"],
                    background=C["surface2"],
                    foreground=C["text"],
                    arrowcolor=C["primary"],
                    selectbackground=C["primary"])
        s.map("TCombobox", fieldbackground=[("readonly", C["surface2"])])

    # ── UI ────────────────────────────────────────────────────────

    def _build(self):
        # ── Sidebar ───────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=C["surface"], width=260)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo area
        logo = tk.Frame(sidebar, bg=C["surface"])
        logo.pack(fill="x", pady=(24,0), padx=20)

        tk.Label(logo, text="✦", font=("Sans", 28),
                 bg=C["surface"], fg=C["primary"]).pack(anchor="w")
        tk.Label(logo, text="Portrait\nSplit",
                 font=("Sans", 18, "bold"),
                 bg=C["surface"], fg=C["text"],
                 justify="left").pack(anchor="w")
        tk.Label(logo, text="v2  •  by AutoPro UG",
                 font=("Sans", 8),
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w", pady=(2,0))

        # Divider
        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", pady=20, padx=20)

        # ── File inputs ───────────────────────────────────────────
        tk.Label(sidebar, text="INPUT VIDEO", font=("Sans", 8, "bold"),
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w", padx=20)

        self.v_input = tk.StringVar()
        dz1 = FileDropZone(sidebar, self.v_input,
                           "Select source MP4", mode="file")
        dz1.pack(fill="x", padx=20, pady=(4,12))

        tk.Label(sidebar, text="OUTPUT FOLDER", font=("Sans", 8, "bold"),
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w", padx=20)

        self.v_output = tk.StringVar()
        dz2 = FileDropZone(sidebar, self.v_output,
                           "Select output folder", mode="dir")
        dz2.pack(fill="x", padx=20, pady=(4,12))

        # Base name
        tk.Label(sidebar, text="BASE FILENAME  (optional)",
                 font=("Sans", 8, "bold"),
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w", padx=20)
        self.v_name = tk.StringVar()
        e = tk.Entry(sidebar, textvariable=self.v_name,
                     font=("Monospace", 9),
                     bg=C["surface2"], fg=C["text"],
                     insertbackground=C["text"],
                     relief="flat", bd=6,
                     highlightthickness=1,
                     highlightbackground=C["border"],
                     highlightcolor=C["primary"])
        e.pack(fill="x", padx=20, pady=(4,0))
        tk.Label(sidebar, text="e.g. Speaker Name — Event 2026",
                 font=("Sans", 7), bg=C["surface"],
                 fg=C["text3"]).pack(anchor="w", padx=20, pady=(2,0))

        # ── Action buttons ────────────────────────────────────────
        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", pady=20, padx=20)

        self.btn_start = ModernButton(sidebar, "▶  Start Processing",
                                      command=self._start,
                                      style="primary", width=220, height=44)
        self.btn_start.pack(padx=20, pady=(0,8))

        self.btn_stop = ModernButton(sidebar, "⏹  Stop",
                                     command=self._stop,
                                     style="danger", width=220, height=36)
        self.btn_stop.pack(padx=20)

        # Status dot
        self._status_frame = tk.Frame(sidebar, bg=C["surface"])
        self._status_frame.pack(pady=16, padx=20, anchor="w")
        self._dot = tk.Label(self._status_frame, text="●",
                             font=("Sans", 10),
                             bg=C["surface"], fg=C["text3"])
        self._dot.pack(side="left")
        self._status_lbl = tk.Label(self._status_frame, text="Ready",
                                    font=("Sans", 9),
                                    bg=C["surface"], fg=C["text3"])
        self._status_lbl.pack(side="left", padx=(4,0))

        # ── Main panel ────────────────────────────────────────────
        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="right", fill="both", expand=True)

        # Tab strip
        tab_bar = tk.Frame(main, bg=C["bg"])
        tab_bar.pack(fill="x", padx=20, pady=(20,0))

        self._tabs = {}
        self._active_tab = tk.StringVar(value="settings")
        for name, icon in [("settings","⚙"), ("log","📋")]:
            btn = tk.Button(tab_bar,
                            text=f"{icon}  {name.title()}",
                            font=("Sans", 9, "bold"),
                            bg=C["primary"] if name=="settings" else C["surface2"],
                            fg=C["text"],
                            relief="flat", bd=0,
                            padx=16, pady=8,
                            cursor="hand2",
                            command=lambda n=name: self._switch_tab(n))
            btn.pack(side="left", padx=(0,4))
            self._tabs[name] = btn

        # Tab content area
        self._tab_content = tk.Frame(main, bg=C["bg"])
        self._tab_content.pack(fill="both", expand=True, padx=20, pady=12)

        self._settings_frame = self._build_settings(self._tab_content)
        self._log_frame      = self._build_log(self._tab_content)
        self._settings_frame.pack(fill="both", expand=True)

    def _switch_tab(self, name):
        self._active_tab.set(name)
        for n, btn in self._tabs.items():
            btn.configure(bg=C["primary"] if n==name else C["surface2"])
        self._settings_frame.pack_forget()
        self._log_frame.pack_forget()
        if name == "settings":
            self._settings_frame.pack(fill="both", expand=True)
        else:
            self._log_frame.pack(fill="both", expand=True)

    def _build_settings(self, parent):
        frame = tk.Frame(parent, bg=C["bg"])

        # ── 2-column grid of cards ────────────────────────────────
        grid = tk.Frame(frame, bg=C["bg"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def card(parent, title, row, col, rowspan=1):
            f = tk.Frame(parent, bg=C["surface"],
                         highlightthickness=1,
                         highlightbackground=C["border"])
            f.grid(row=row, column=col, padx=6, pady=6,
                   sticky="nsew", rowspan=rowspan)
            tk.Label(f, text=title, font=("Sans", 9, "bold"),
                     bg=C["surface"], fg=C["primary"]).pack(
                         anchor="w", padx=16, pady=(14,6))
            tk.Frame(f, bg=C["border"], height=1).pack(fill="x", padx=12)
            return f

        # Card 1 — Splitting
        c1 = card(grid, "✂  Splitting", 0, 0)
        self.v_segment  = tk.IntVar(value=200)
        self.v_parallel = tk.IntVar(value=4)
        self._spin_row(c1, "Segment length (seconds)", self.v_segment,  60, 600)
        self._spin_row(c1, "Parallel segments",         self.v_parallel, 1,  8)
        tk.Label(c1, text="More parallel = faster but uses more CPU & RAM",
                 font=("Sans", 7), bg=C["surface"],
                 fg=C["text3"]).pack(anchor="w", padx=16, pady=(0,14))

        # Card 2 — Quality
        c2 = card(grid, "🎞  Quality & Encoding", 0, 1)
        self.v_crf = tk.IntVar(value=18)
        self._spin_row(c2, "CRF quality  (0 = lossless, 18 = near-lossless)",
                       self.v_crf, 0, 35)
        tk.Label(c2, text="ENCODING PRESET", font=("Sans", 8, "bold"),
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w", padx=16, pady=(10,2))
        self.v_preset = tk.StringVar(value="fast")
        combo = ttk.Combobox(c2, textvariable=self.v_preset,
                             values=["ultrafast","superfast","veryfast",
                                     "faster","fast","medium","slow"],
                             state="readonly", width=14)
        combo.pack(anchor="w", padx=16)
        tk.Label(c2, text="ultrafast = quickest · slow = smallest file",
                 font=("Sans", 7), bg=C["surface"],
                 fg=C["text3"]).pack(anchor="w", padx=16, pady=(2,14))

        # Card 3 — Camera tracking
        c3 = card(grid, "🎯  Camera Tracking", 1, 0)
        self.v_smooth    = tk.DoubleVar(value=0.3)
        self.v_max_jump  = tk.IntVar(value=400)
        self.v_max_drift = tk.IntVar(value=6)
        Slider(c3, "Tracking speed  (0.1 = smooth · 1.0 = instant)",
               self.v_smooth, 0.05, 1.0).pack(fill="x", padx=16, pady=(10,6))
        self._spin_row(c3, "Max jump (px) — ignore far faces",
                       self.v_max_jump, 100, 960)
        self._spin_row(c3, "Max drift (px/frame) — pan speed limit",
                       self.v_max_drift, 1, 30)
        tk.Label(c3, text="Lower drift = smoother pan, higher = snappier follow",
                 font=("Sans", 7), bg=C["surface"],
                 fg=C["text3"]).pack(anchor="w", padx=16, pady=(0,14))

        # Card 4 — Stats
        c4 = card(grid, "📊  Session Stats", 1, 1)
        self._stat_vars = {}
        for label in ("Parts completed", "Processing speed", "ETA"):
            row_f = tk.Frame(c4, bg=C["surface"])
            row_f.pack(fill="x", padx=16, pady=4)
            tk.Label(row_f, text=label, font=("Sans", 8),
                     bg=C["surface"], fg=C["text3"]).pack(side="left")
            v = tk.StringVar(value="—")
            self._stat_vars[label] = v
            tk.Label(row_f, textvariable=v,
                     font=("Monospace", 9, "bold"),
                     bg=C["surface"], fg=C["text"]).pack(side="right")

        # Progress bar
        pb_frame = tk.Frame(c4, bg=C["surface"])
        pb_frame.pack(fill="x", padx=16, pady=(12,14))
        tk.Label(pb_frame, text="Progress", font=("Sans", 8),
                 bg=C["surface"], fg=C["text3"]).pack(anchor="w")
        self._progress = ttk.Progressbar(pb_frame, mode="indeterminate",
                                         length=200)
        self._progress.pack(fill="x", pady=(4,0))

        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        return frame

    def _build_log(self, parent):
        frame = tk.Frame(parent, bg=C["bg"])
        top = tk.Frame(frame, bg=C["bg"])
        top.pack(fill="x", pady=(0,6))
        tk.Label(top, text="Live output", font=("Sans", 9, "bold"),
                 bg=C["bg"], fg=C["text2"]).pack(side="left")
        ModernButton(top, "Clear", command=lambda: self._logbox.clear(),
                     style="ghost", width=80, height=28).pack(side="right")
        self._logbox = LogBox(frame)
        self._logbox.pack(fill="both", expand=True)
        return frame

    def _spin_row(self, parent, label, var, from_, to):
        f = tk.Frame(parent, bg=C["surface"])
        f.pack(fill="x", padx=16, pady=(8,0))
        tk.Label(f, text=label, font=("Sans", 8),
                 bg=C["surface"], fg=C["text2"]).pack(side="left")
        sb = tk.Spinbox(f, from_=from_, to=to, textvariable=var,
                        width=5, font=("Monospace", 9),
                        bg=C["surface2"], fg=C["text"],
                        buttonbackground=C["border"],
                        insertbackground=C["text"],
                        relief="flat", bd=3)
        sb.pack(side="right")

    # ── Logic ─────────────────────────────────────────────────────

    def _set_status(self, text, color=C["text3"]):
        self._dot.configure(fg=color)
        self._status_lbl.configure(text=text, fg=color)

    def _start(self):
        src = self.v_input.get().strip()
        if not src or not Path(src).is_file():
            messagebox.showerror("No input", "Please select a valid MP4 file.")
            return
        out = self.v_output.get().strip()
        if not out:
            # default: alongside source
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

        self._running = True
        self._set_status("Processing …", C["primary"])
        self._progress.start(10)
        self._switch_tab("log")
        self._logbox.clear()
        self._logbox.append(f"▶  Portrait Split v2", "head")
        self._logbox.append(f"   Input  : {src}")
        self._logbox.append(f"   Output : {out}")
        self._logbox.append(f"   Parts  : {seg}s each  |  parallel {par}")
        self._logbox.append("")

        threading.Thread(target=self._worker,
                         args=(src, out, name, seg, smooth,
                               crf, preset, par, jump, drift),
                         daemon=True).start()

    def _worker(self, src, out, name, seg, smooth,
                crf, preset, par, jump, drift):
        script = Path(__file__).parent / "portrait_split.py"
        cmd = [
            sys.executable, str(script),
            "-i", src, "-o", out, "-n", name,
            "-s", str(seg),
            "--smooth",     str(smooth),
            "--crf",        str(crf),
            "--preset",     preset,
            "--parallel",   str(par),
            "--max-jump",   str(jump),
            "--max-drift",  str(drift),
        ]
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                if not self._running:
                    self._proc.terminate()
                    break
                line = line.rstrip()
                tag = ("ok" if "✅" in line or "Done" in line
                       else "warn" if "warn" in line.lower()
                       else "err"  if "error" in line.lower()
                       else None)
                # parse stats from log lines
                if "fps" in line.lower() and "frame" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "fps" and i > 0:
                            self._log_q.put(("stat", "Processing speed",
                                             f"{parts[i-1]} fps"))
                self._log_q.put(("log", line, tag))
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
        self._reset_ui()

    def _poll_log(self):
        try:
            while True:
                item = self._log_q.get_nowait()
                kind = item[0]
                if kind == "log":
                    _, msg, tag = item
                    self._logbox.append(msg, tag)
                elif kind == "stat":
                    _, key, val = item
                    if key in self._stat_vars:
                        self._stat_vars[key].set(val)
                elif kind == "done":
                    self._logbox.append("\n🎉  All parts complete!", "ok")
                    self._set_status("Done", C["success"])
                    self._reset_ui()
        except queue.Empty:
            pass
        self.after(80, self._poll_log)

    def _reset_ui(self):
        self._running = False
        self._progress.stop()
        if not self._status_lbl.cget("text").startswith("Done"):
            self._set_status("Ready", C["text3"])


def main():
    mp.set_start_method("spawn", force=True)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
