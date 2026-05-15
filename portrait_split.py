#!/usr/bin/env python3
"""
portrait_split.py — core engine
Called directly or imported by the GUI.
"""

import argparse
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

OUT_W, OUT_H  = 1080, 1920
DETECT_SCALE  = 0.25
DETECT_EVERY  = 5
WRITE_BATCH   = 16
MAX_JUMP_PX   = 400
MAX_DRIFT_PX  = 6
PRE_SEEK_S    = 5.0


def _ema(cur, tgt, a):
    return cur + a * (tgt - cur)


def _detect_cx(small_gray, scale_inv, cascade):
    faces = cascade.detectMultiScale(
        small_gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(20, 20), flags=cv2.CASCADE_SCALE_IMAGE,
    )
    if not isinstance(faces, np.ndarray) or len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return int((x + w // 2) * scale_inv)


def _make_portrait(frame, src_w, src_h, cx):
    crop_w = max(1, min(int(src_h * OUT_W / OUT_H), src_w))
    x0     = max(0, min(cx - crop_w // 2, src_w - crop_w))
    return cv2.resize(frame[:, x0: x0 + crop_w], (OUT_W, OUT_H),
                      interpolation=cv2.INTER_LINEAR)


def _two_step_seek(start_sec):
    pre  = min(PRE_SEEK_S, start_sec)
    fast = start_sec - pre
    return fast, pre


def _open_encoder(path, fps, crf, preset):
    return subprocess.Popen(
        ["ffmpeg", "-y",
         "-f", "rawvideo", "-vcodec", "rawvideo",
         "-s", f"{OUT_W}x{OUT_H}", "-pix_fmt", "bgr24",
         "-r", str(fps), "-i", "pipe:0",
         "-an", "-c:v", "libx264",
         "-crf", str(crf), "-preset", preset,
         "-pix_fmt", "yuv420p", path],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _extract_audio(src, start_sec, dur_sec, dst):
    fast, pre = _two_step_seek(start_sec)
    subprocess.run(
        ["ffmpeg", "-y",
         "-ss", f"{fast:.6f}", "-i", src,
         "-ss", f"{pre:.6f}",
         "-t",  f"{dur_sec:.6f}",
         "-vn", "-c:a", "aac", "-b:a", "128k", dst],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _mux(vid, aud, out):
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", vid, "-i", aud,
         "-map", "0:v", "-map", "1:a", "-c", "copy", out],
        capture_output=True,
    )
    if r.returncode != 0:
        print(f"  [warn] mux: {r.stderr.decode()[-200:]}", flush=True)


def _process_segment(task):
    src       = task["src"]
    part      = task["part"]
    n_parts   = task["n_parts"]
    start_sec = task["start_sec"]
    dur_sec   = task["dur_sec"]
    fps       = task["fps"]
    src_w     = task["src_w"]
    src_h     = task["src_h"]
    smooth    = task["smooth"]
    crf       = task["crf"]
    preset    = task["preset"]
    final_out = task["final_out"]
    det_every = task["detect_every"]
    det_scale = task["detect_scale"]
    max_jump  = task["max_jump"]
    max_drift = task["max_drift"]
    log_q     = task.get("log_q")         # optional multiprocessing.Queue

    def log(msg):
        print(msg, flush=True)
        if log_q:
            try: log_q.put(msg)
            except: pass

    tag       = f"Part {part}/{n_parts}"
    scale_inv = 1.0 / det_scale
    raw_bytes = src_w * src_h * 3
    batch_sz  = OUT_W * OUT_H * 3 * WRITE_BATCH

    _casc = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(_casc)

    tmp_vid = tempfile.NamedTemporaryFile(suffix=f"_p{part}_vid.mp4", delete=False)
    tmp_aud = tempfile.NamedTemporaryFile(suffix=f"_p{part}_aud.aac", delete=False)
    tmp_vid.close(); tmp_aud.close()

    fast_seek, pre_seek = _two_step_seek(start_sec)

    decoder = subprocess.Popen(
        ["ffmpeg",
         "-ss", f"{fast_seek:.6f}", "-i", src,
         "-ss", f"{pre_seek:.6f}",
         "-t",  f"{dur_sec:.6f}",
         "-f",  "rawvideo", "-pix_fmt", "bgr24", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    encoder = _open_encoder(tmp_vid.name, fps, crf, preset)

    smooth_cx = float(src_w // 2)
    last_cx   = src_w // 2
    no_face   = 0
    idx       = 0
    write_buf = bytearray()
    total_f   = int(dur_sec * fps)

    log(f"  {tag}  starting …")

    while True:
        raw = decoder.stdout.read(raw_bytes)
        if len(raw) < raw_bytes:
            break
        frame = np.frombuffer(raw, dtype=np.uint8).reshape((src_h, src_w, 3))

        if idx % det_every == 0:
            small   = cv2.resize(frame, None, fx=det_scale, fy=det_scale,
                                 interpolation=cv2.INTER_NEAREST)
            gray    = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            face_cx = _detect_cx(gray, scale_inv, cascade)
            if face_cx is not None:
                if abs(face_cx - smooth_cx) <= max_jump:
                    last_cx, no_face = face_cx, 0
            else:
                no_face += det_every
                if no_face > fps * 3:
                    last_cx = src_w // 2

        new_cx = _ema(smooth_cx, float(last_cx), smooth)
        delta  = new_cx - smooth_cx
        if abs(delta) > max_drift:
            new_cx = smooth_cx + max_drift * (1 if delta > 0 else -1)
        smooth_cx = new_cx
        cx = int(round(smooth_cx))

        portrait = _make_portrait(frame, src_w, src_h, cx)
        write_buf.extend(portrait.tobytes())
        if len(write_buf) >= batch_sz:
            encoder.stdin.write(bytes(write_buf))
            write_buf.clear()

        idx += 1
        if idx % 300 == 0:
            pct = idx / max(total_f, 1) * 100
            log(f"  {tag}  [{pct:5.1f}%]  frame {idx}/{total_f}")

    if write_buf:
        encoder.stdin.write(bytes(write_buf))

    decoder.stdout.close(); decoder.wait()
    encoder.stdin.close();  encoder.wait()

    log(f"  {tag}  extracting audio …")
    _extract_audio(src, start_sec, dur_sec, tmp_aud.name)
    log(f"  {tag}  muxing …")
    _mux(tmp_vid.name, tmp_aud.name, final_out)

    for f in (tmp_vid.name, tmp_aud.name):
        try: os.remove(f)
        except OSError: pass

    log(f"  ✅ {tag}  →  {Path(final_out).name}")
    return part


def build_tasks(src, out_dir, base_name, seg_sec,
                smooth, crf, preset,
                detect_every, detect_scale,
                max_jump, max_drift, log_q=None):

    src_path = Path(src).expanduser().resolve()
    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    cap   = cv2.VideoCapture(str(src_path))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur_s = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    cap.release()

    tasks, part, t = [], 1, 0.0
    while t < dur_s:
        actual = min(seg_sec, dur_s - t)
        if actual < 1:
            break
        tasks.append({
            "src":          str(src_path),
            "part":         part,
            "n_parts":      0,
            "start_sec":    t,
            "dur_sec":      actual,
            "fps":          fps,
            "src_w":        src_w,
            "src_h":        src_h,
            "smooth":       smooth,
            "crf":          crf,
            "preset":       preset,
            "final_out":    str(out_path / f"{base_name}_part{part}.mp4"),
            "detect_every": detect_every,
            "detect_scale": detect_scale,
            "max_jump":     max_jump,
            "max_drift":    max_drift,
            "log_q":        log_q,
        })
        t += seg_sec; part += 1

    n = len(tasks)
    for tk in tasks:
        tk["n_parts"] = n
    return tasks, fps, src_w, src_h, dur_s


def run(src, out_dir, base_name, seg_sec, smooth, crf, preset,
        parallel, detect_every, detect_scale, max_jump, max_drift,
        log_q=None):

    tasks, fps, src_w, src_h, dur_s = build_tasks(
        src, out_dir, base_name, seg_sec,
        smooth, crf, preset,
        detect_every, detect_scale, max_jump, max_drift, log_q,
    )
    n_parts = len(tasks)

    def log(m):
        print(m, flush=True)
        if log_q:
            try: log_q.put(m)
            except: pass

    log(f"\n{'━'*65}")
    log(f"  Source   : {Path(src).name}")
    log(f"  Size     : {src_w}×{src_h}  {fps:.2f} fps  {dur_s:.1f}s")
    log(f"  Output   : {OUT_W}×{OUT_H} portrait  CRF {crf}  {preset}")
    log(f"  Segments : {seg_sec}s each  →  {n_parts} parts")
    log(f"  Parallel : {parallel}")
    log(f"{'━'*65}\n")

    completed = 0
    with mp.Pool(processes=parallel) as pool:
        for _ in pool.imap_unordered(_process_segment, tasks):
            completed += 1
            log(f"\n  ── {completed}/{n_parts} complete ──\n")

    log(f"\n🎉  Done!  {n_parts} portrait parts saved to:\n    {out_dir}")


# ── CLI ───────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Portrait split + face tracking")
    ap.add_argument("-i", "--input",      required=True)
    ap.add_argument("-o", "--output",     default=None)
    ap.add_argument("-n", "--name",       default=None)
    ap.add_argument("-s", "--segment",    type=int,   default=200)
    ap.add_argument("--smooth",           type=float, default=0.3)
    ap.add_argument("--crf",              type=int,   default=18)
    ap.add_argument("--preset",           default="fast")
    ap.add_argument("--parallel",         type=int,   default=4)
    ap.add_argument("--detect-every",     type=int,   default=DETECT_EVERY)
    ap.add_argument("--detect-scale",     type=float, default=DETECT_SCALE)
    ap.add_argument("--max-jump",         type=int,   default=MAX_JUMP_PX)
    ap.add_argument("--max-drift",        type=int,   default=MAX_DRIFT_PX)
    args = ap.parse_args()

    src     = Path(args.input).expanduser().resolve()
    out_dir = args.output or str(src.parent / (src.stem + "_portrait"))
    name    = args.name or src.stem
    if not src.is_file():
        sys.exit(f"ERROR: '{src}' not found.")

    run(str(src), out_dir, name,
        args.segment, args.smooth, args.crf, args.preset,
        args.parallel, args.detect_every, args.detect_scale,
        args.max_jump, args.max_drift)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
