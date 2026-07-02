"""Pickleball Linecaller — Phase 2 (§5.1–5.9) hand-off package.

Status legend: [done] runs today · [placeholder] tagged PLACEHOLDER[ID],
see PLACEHOLDER_COOKBOOK.md for the recipe that fills it.

    court_model  [done]         canonical 12-keypoint court, line calls
    config       [done]         config.yaml access
    calibration  [done + KPT-1] checkerboard intrinsics, homography, PnP
    placement    [done + PLC-1] §5.4 readiness/state machine (audio stub)
    sync         [done]         clap detection + xcorr refinement
    tracking     [TRK-1/TRK-2]  GridTrackNet wrapper (MockTracker runs now)
    bounce       [done + BNC-1] separation signal s(t), V-shape, sub-frame
    fusion       [done]         weighted fusion, dispute rule, audit trail
    pipeline     [done]         clip pair -> line calls (injectable parts)
    server       [ARCH-1]       §5.9 real-time skeleton
"""

from .bounce import BounceEvent, detect_bounces
from .calibration import (CourtCalibration, Intrinsics,
                          calibrate_intrinsics_from_video,
                          fit_court_homography, solve_camera_pose)
from .config import Config
from .court_model import COURT_PTS_FT, KEYPOINTS, line_call
from .fusion import LineCall, fuse_event
from .pipeline import run_clip_pair
from .tracking import BallTrack, GridTrackNetTracker, MockTracker

__version__ = "0.1.0"
