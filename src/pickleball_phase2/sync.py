"""Clip synchronization from the per-clip clap cue — §7.2.

Implemented: audio extraction (ffmpeg), energy-envelope clap detection,
cross-correlation refinement. Tune on your real clips (Recipe 4).
"""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


def extract_audio_mono(video_path: str | Path, sr: int = 16000) -> tuple[np.ndarray, int]:
    """Decode a video's audio track to mono float32 via ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
           "-ac", "1", "-ar", str(sr), "-vn", wav_path]
    subprocess.run(cmd, check=True)
    with wave.open(wav_path, "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
        width = w.getsampwidth()
    if width != 2:
        raise RuntimeError(f"expected 16-bit wav, got sample width {width}")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    Path(wav_path).unlink(missing_ok=True)
    return x, sr


def find_clap_s(
    audio: np.ndarray, sr: int,
    search_window_s: float = 5.0,
    energy_win_ms: float = 10.0,
) -> float:
    """Time (s) of the clap: the sharpest short-window energy onset near the start.

    Simple and robust for a clean clap; if your courts were windy/noisy,
    tune the window or fall back to manual sync (Recipe 4).
    """
    n = min(len(audio), int(search_window_s * sr))
    x = audio[:n]
    win = max(1, int(energy_win_ms / 1000.0 * sr))
    e = np.convolve(x ** 2, np.ones(win) / win, mode="same")
    onset = np.diff(e, prepend=e[0])
    return float(np.argmax(onset) / sr)


def refine_offset_xcorr(
    audio_a: np.ndarray, audio_b: np.ndarray, sr: int,
    coarse_offset_s: float, half_window_s: float = 0.5,
) -> float:
    """Refine A->B offset to sub-frame precision by cross-correlating the
    audio around the clap. Returns refined offset in seconds (positive =
    B lags A)."""
    max_lag = int(half_window_s * sr)
    coarse = int(coarse_offset_s * sr)
    seg = audio_a[: sr * 8]
    lags = range(coarse - max_lag, coarse + max_lag + 1)
    best_lag, best_val = coarse, -np.inf
    for lag in lags:
        if lag >= 0:
            a, b = seg[: len(seg) - lag], audio_b[lag: lag + len(seg)]
        else:
            a, b = seg[-lag:], audio_b[: len(seg) + lag]
        m = min(len(a), len(b))
        if m < sr // 10:
            continue
        v = float(np.dot(a[:m], b[:m]))
        if v > best_val:
            best_val, best_lag = v, lag
    return best_lag / sr


def frame_offset(video_a: str | Path, video_b: str | Path,
                 fps: float = 60.0, cfg: dict | None = None) -> float:
    """End-to-end: fractional frame offset between the clips.

    Convention: aligned_frame = frame_B - offset. Positive offset means the
    clap appears LATER in B's timeline (B started recording earlier).
    pipeline.py therefore passes -offset to the B tracker (which ADDS it)."""
    cfg = cfg or {}
    aud_a, sr = extract_audio_mono(video_a)
    aud_b, _ = extract_audio_mono(video_b)
    window = cfg.get("clap_search_window_s", 5.0)
    win_ms = cfg.get("energy_win_ms", 10.0)
    ta = find_clap_s(aud_a, sr, window, win_ms)
    tb = find_clap_s(aud_b, sr, window, win_ms)
    off_s = tb - ta
    if cfg.get("refine_with_xcorr", True):
        off_s = refine_offset_xcorr(aud_a, aud_b, sr, off_s)
    return off_s * fps
