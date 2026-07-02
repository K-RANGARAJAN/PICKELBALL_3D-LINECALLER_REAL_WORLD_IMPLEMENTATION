# Pickleball Linecaller - Phase 2 Hand-off Package

Implementation skeleton for **§5.1–5.9** of the Technical Disclosure
(*Pickleball Linecaller — A Two-Camera Computer-Vision System*, June 2026)
plus the **Dual Ground-Plane Homography** derivation (separation-signal
bounce detection). Built to be handed to future interns: every gap is a
tagged `PLACEHOLDER[ID]` with a matching recipe in
[`PLACEHOLDER_COOKBOOK.md`](PLACEHOLDER_COOKBOOK.md).

**Phase 1** (single-camera court calibration, completed) lives at:
https://github.com/K-RANGARAJAN/Pickleball-automatic-court-calibration

## The idea in one paragraph

Two phones behind the near-baseline corners each calibrate themselves to the
court by detecting 12 line-intersection keypoints and fitting a RANSAC
homography to the canonical court model — so both views share one coordinate
frame. Each phone's ball track is projected through its homography onto the
court plane. While the ball is airborne the two projections **disagree**;
at contact (Z = 0) they **converge**. The minimum of the separation signal
s(t) = ‖G_A − G_B‖ is the bounce; sub-frame refinement fixes 60 fps
undersampling; weighted fusion + a dispute rule produce the IN/OUT call
with a full audit trail.

## Layout

```
config.yaml                 every path & threshold (TUNE-* = to calibrate)
PLACEHOLDER_COOKBOOK.md     step-by-step recipes to fill every placeholder
CLAUDE.md                   AI agent team used to develop/extend this repo
src/pickleball_phase2/
    court_model.py     [done]   canonical court, keypoints, line_call
    config.py          [done]   config access
    calibration.py     [KPT-1]  intrinsics ✓, homography ✓, PnP ✓, keypoint model ✗
    placement.py       [PLC-1]  §5.4 readiness + state machine ✓, audio ✗
    sync.py            [done]   clap detect + xcorr refine (tune on real clips)
    tracking.py        [TRK-1,2] GridTrackNet wrapper ✗ (MockTracker ✓)
    bounce.py          [BNC-1]  s(t) ✓, minima ✓, V-shape ✓, sub-frame ✓, classifier ✗
    fusion.py          [done]   weights, dispute rule, audit (TUNE-3/4 to calibrate)
    pipeline.py        [done]   clip pair -> LineCalls (all parts injectable)
    server.py          [ARCH-1] §5.9 real-time skeleton
tests/test_smoke.py    [done]   synthetic end-to-end — runs with zero data
data/                  put captures here (see data/README.md)
```

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate   # python 3.10
pip install -r requirements.txt
python -m pytest tests/ -q        # should pass TODAY, before any data work
```

Then open the cookbook and start at **Recipe 0**.

## Status board (update as recipes complete)

| Recipe | Placeholder | Status | Owner | Notes |
|--------|-------------|--------|-------|-------|
| 0 Kitchen setup | — | ☐ | | |
| 1 Intrinsics | — (code done; run it) | ☐ | | checkerboard videos to record |
| 2 Keypoint model | KPT-1 | ☐ | | calibration clips collected ✓ |
| 3 Calibration check | — | ☐ | | |
| 4 Sync check | — (tuning only) | ☐ | | clap cue present in every clip ✓ |
| 5 Tracker | TRK-1/2 | ☐ | | GridTrackNet = TF, py3.10, MIT |
| 6 Bounce tuning | TUNE-2, BNC-1 | ☐ | | |
| 7 Fusion calibration | TUNE-3/4 | ☐ | | no taped markers — use slow-mo labels |
| 8 Beeps | PLC-1 | ☐ | | optional |
| 9 Real-time server | ARCH-1 | ☐ | | future intern project |

## Data collected so far (June–July 2026)

Per the §7 methodology: court-calibration clips (empty court), synced A/B
rally + bounce footage with per-clip clap cue, camera K kitchen footage,
4 courts, multiple lighting conditions. Checkerboard intrinsics videos:
**to be recorded** (Recipe 1). Taped ground-truth markers: **not captured**
— Recipe 7 includes the slow-mo fallback.

## Design decisions a future intern should not re-litigate

1. **No wide-baseline stereo.** Ill-conditioned at this geometry (§5.6).
   Height is never estimated; contact is detected via cross-view
   convergence of ground projections (see the derivation doc).
2. **Homography is the product; PnP is a diagnostic.** Line calls need only
   ground-plane (X, Y). PnP recovers camera pose to sanity-check the rig
   against measured positions.
3. **Feet everywhere.** The canonical frame is in feet (§4.1); convert to cm
   only for reporting (`court_model.FT_TO_CM`).
4. **Everything injectable.** Trackers and calibrations are constructor/
   function arguments, so any half-finished placeholder state still runs
   end-to-end with mocks — that's how the tests work.
