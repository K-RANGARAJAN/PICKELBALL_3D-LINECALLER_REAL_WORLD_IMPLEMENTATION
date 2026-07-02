"""Ball detection & tracking — §5.5 (GridTrackNet wrapper).

The wrapper interface is final; the GridTrackNet glue is PLACEHOLDER[TRK-1]
and the pickleball fine-tune is PLACEHOLDER[TRK-2] (Cookbook Recipe 5).
`MockTracker` lets the rest of the pipeline run today (used by the tests).

GridTrackNet facts (verified from the repo, MIT license):
  - TensorFlow/Keras, python 3.10; weights file `model_weights.h5`
  - 5 input frames -> 5 output frames, input 768x432, output grid 48x27
  - API: Predict.getPredictions(frames, isBGRFormat=...) -> per-frame
    (x, y) pixel coords; (0, 0) means "no ball". The flag must match your
    frame source: cv2.VideoCapture yields BGR -> pass isBGRFormat=True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class BallTrack:
    """Per-camera ball track. Arrays share length N (one entry per frame)."""

    frames: np.ndarray          # (N,) int frame indices (aligned timeline)
    uv: np.ndarray              # (N, 2) float pixel positions
    conf: np.ndarray            # (N,) float detection confidence [0, 1]
    valid: np.ndarray           # (N,) bool — False where no ball was found
    fps: float = 60.0
    meta: dict = field(default_factory=dict)

    def valid_only(self) -> "BallTrack":
        m = self.valid
        return BallTrack(self.frames[m], self.uv[m], self.conf[m],
                         np.ones(int(m.sum()), dtype=bool), self.fps, self.meta)


class BaseTracker:
    def track_video(self, video_path: str | Path, frame_offset: float = 0.0) -> BallTrack:
        raise NotImplementedError


class GridTrackNetTracker(BaseTracker):
    """PLACEHOLDER[TRK-1] + [TRK-2] — real GridTrackNet inference.

    Recipe 5 walks through: cloning the repo, loading `model_weights.h5`,
    feeding frames in batches of 5 at 768x432, mapping grid outputs back to
    1920x1080 pixel coords, and fine-tuning on pickleball frames.
    """

    def __init__(self, weights_path: str | Path, repo_path: str | Path,
                 min_confidence: float = 0.30):
        self.weights_path = Path(weights_path)
        self.repo_path = Path(repo_path)
        self.min_confidence = min_confidence

    def track_video(self, video_path: str | Path, frame_offset: float = 0.0) -> BallTrack:
        raise NotImplementedError(
            "PLACEHOLDER[TRK-1] — see PLACEHOLDER_COOKBOOK.md, Recipe 5")


class MockTracker(BaseTracker):
    """Injectable fake for tests/demos: returns a pre-computed track."""

    def __init__(self, track: BallTrack):
        self._track = track

    def track_video(self, video_path: str | Path, frame_offset: float = 0.0) -> BallTrack:
        t = self._track
        return BallTrack(t.frames + frame_offset, t.uv, t.conf, t.valid, t.fps, t.meta)


def smooth_track(track: BallTrack, window: int = 5) -> BallTrack:
    """Light moving-average smoothing over valid detections (stand-in for the
    Kalman filter of the derivation doc, step 2 — upgrade freely)."""
    t = track.valid_only()
    if len(t.frames) < window:
        return t
    k = np.ones(window) / window
    uv = np.stack([np.convolve(t.uv[:, 0], k, mode="same"),
                   np.convolve(t.uv[:, 1], k, mode="same")], axis=1)
    return BallTrack(t.frames, uv, t.conf, t.valid, t.fps, t.meta)
