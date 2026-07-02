# 🍳 The Placeholder Cookbook

Every gap in this codebase is tagged in the source as `PLACEHOLDER[ID]`.
Each recipe below fills one ID. Follow them **in order** — later recipes
assume earlier ones are done. Grep for the ID to find the exact spot:

```bash
grep -rn "PLACEHOLDER\[" src/
```

**Recipe order & dependency map**

| # | Recipe | Fills | Needs recipes | You need (data/assets) |
|---|--------|-------|--------------|------------------------|
| 0 | Kitchen setup | — | — | this repo, Python 3.10 |
| 1 | Phone intrinsics | — (code done; produces yamls) | 0 | checkerboard videos per phone |
| 2 | Real-world keypoint model | KPT-1 | 0 | empty-court calibration clips |
| 3 | Per-camera calibration check | — | 1, 2 | court measurements |
| 4 | Clap sync check | — (tuning only) | 0 | any synced clip pair |
| 5 | GridTrackNet tracker | TRK-1, TRK-2 | 0 | GridTrackNet repo + rally clips |
| 6 | Bounce tuning + classifier | TUNE-2, BNC-1 | 2, 4, 5 | rally + staged bounce clips |
| 7 | Fusion calibration | TUNE-3, TUNE-4 | 6 | ground-truth or slow-mo labels |
| 8 | Placement beeps | PLC-1 | — (optional) | a speaker |
| 9 | Real-time server | ARCH-1 | 1–7 | GPU machine |

---

## Recipe 0 — Kitchen setup (do this first)

**You need:** Python **3.10** (GridTrackNet requires it), this repo.

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Prove the kitchen works before cooking anything:
   ```bash
   python -m pytest tests/ -q
   ```

✅ **Done when:** all tests pass. They exercise the real geometry — homography,
separation signal s(t), sub-frame refinement, fusion, line calls — on
synthetic data. If these fail, nothing else will work; fix this first.

---

## Recipe 1 — Phone intrinsics *(code already done — you just run it)*

**You need:** the ~60 s checkerboard sweep video for EACH phone, shot at the
exact locked capture settings (§5.2); the measured square size in mm.

1. Update `config.yaml -> checkerboard.square_size_mm` with YOUR measured
   value (TUNE-0). Do not trust the nominal print size — measure with a ruler.
2. For each phone:
   ```python
   from pickleball_phase2.calibration import calibrate_intrinsics_from_video
   intr = calibrate_intrinsics_from_video("data/raw/S1_camA_checkerboard.mp4",
                                          inner_corners=(9, 6), square_size_mm=25.0)
   print(intr.rms)          # expect < 1.0 px
   intr.save("calib/intrinsics/camA.yaml")
   ```
3. Repeat for camB (and camK).

✅ **Done when:** each camera has a yaml in `calib/intrinsics/` and RMS < 1 px.
⚠️ If RMS > 1.5 px: the sweep was too fast (motion blur) or didn't cover the
frame corners — re-shoot per §7.1.

---

## Recipe 2 — Real-world keypoint model `[KPT-1]` *(the big one)*

**Why:** the Phase-1 model only ever saw elevated broadcast views. Your phone
footage is low, behind-the-corner — a different world. It must be fine-tuned.

**You need:** the empty-court reference clips + a sample of rally clips from
all 4 courts; the Phase-1 training setup (repo: K-RANGARAJAN/
Pickleball-automatic-court-calibration) and its best checkpoint.

1. Extract frames from your real-world clips (~50–150 per court/placement,
   more variety > more frames):
   ```bash
   ffmpeg -i clip.mp4 -vf fps=2 data/frames/court1_%04d.jpg
   ```
2. Annotate the 12 keypoints with the Phase-1 browser annotation editor,
   same index order (Appendix A) and visibility flags (2/1/0). Bootstrap
   trick from §4.3: run the Phase-1 model to pre-label, then drag-correct.
3. Fine-tune FROM the Phase-1 checkpoint (don't start from scratch):
   ```python
   from ultralytics import YOLO
   model = YOLO("phase1_best.pt")
   model.train(data="realworld_court.yaml", imgsz=1280, epochs=60,
               fliplr=0.5, mosaic=0, mixup=0)   # keep the Phase-1 flip_idx!
   ```
   Split by COURT (train on 3, validate on the 4th) — never random frames,
   same anti-leakage logic as §4.2.
4. Copy the best checkpoint to `models/court_keypoints_realworld.pt`
   (the `config.yaml -> paths.keypoint_weights` path).
5. Implement `calibration.detect_court_keypoints()` — replace the raise with:
   ```python
   from ultralytics import YOLO
   _model = YOLO(str(weights_path))          # cache this at module level
   res = _model(frame_bgr, verbose=False)[0]
   kxy = res.keypoints.xy[0].cpu().numpy()          # (12, 2)
   kconf = res.keypoints.conf[0].cpu().numpy()      # (12,)
   # three-level visibility, matching the Phase-1 convention (2/1/0):
   # confident -> visible(2); plausible -> occluded-but-known(1) so it can
   # STILL feed the homography (fit uses vis >= 1); junk -> not-labeled(0)
   vis = np.where(kconf > 0.5, 2.0, np.where(kconf > 0.25, 1.0, 0.0))
   return np.hstack([kxy, vis[:, None]])
   ```

✅ **Done when:** on a held-out court, `lock_on()` over an empty-court clip
returns mean_reproj_px ≤ 8 (the §4.7 lock threshold), ideally ≤ 3.

---

## Recipe 3 — Per-camera calibration check

**You need:** Recipes 1–2 done; the measured camera positions/heights and
court dimensions from the shoot README (§7.1–7.2).

1. Run lock-on on each camera's empty-court reference clip:
   ```python
   from pickleball_phase2.pipeline import calibrate_camera_from_clip
   calib = calibrate_camera_from_clip("data/raw/..._camA_clip001.mp4", cfg)
   print(calib.mean_reproj_px, calib.mean_reproj_ft)
   ```
2. Add PnP and compare against reality:
   ```python
   from pickleball_phase2.calibration import solve_camera_pose, Intrinsics
   intr = Intrinsics.load("calib/intrinsics/camA.yaml")
   calib = solve_camera_pose(kpts, intr, calib)
   print(calib.camera_pos_ft)   # vs your measured (X, Y, height)!
   ```

✅ **Done when:** recovered camera position is within ~1 ft of the tape-measured
position for every camera on every court. Larger error → wrong intrinsics
(Recipe 1) or bad keypoints (Recipe 2).

---

## Recipe 4 — Clap sync check *(code already done — verify + tune)*

**You need:** any A/B clip pair from one session.

1. ```python
   from pickleball_phase2.sync import frame_offset
   off = frame_offset("camA_clip003.mp4", "camB_clip003.mp4", fps=60)
   print(off)   # frames; aligned = frame_B - off
   ```
2. Eyeball-verify: open both clips, find the clap frame in each, subtract.
   Should match `off` within ±1 frame (xcorr refinement gets sub-frame).

✅ **Done when:** automatic offset matches your manual check on 3 different
clip pairs. ⚠️ Windy/noisy courts: raise `sync.energy_win_ms` to 20, or
hard-code the manual offset in the master log and skip auto-sync.

---

## Recipe 5 — GridTrackNet tracker `[TRK-1]`, then fine-tune `[TRK-2]`

**You need:** `git clone https://github.com/VKorpelshoek/GridTrackNet` into
`third_party/GridTrackNet` (MIT license); TensorFlow; Python 3.10.

**Part A — wire the tennis model (TRK-1):**

1. `pip install tensorflow` and copy `model_weights.h5` to
   `models/` (repo root has it).
2. Implement `GridTrackNetTracker.track_video()`. The repo API:
   `Predict.getPredictions(frames, isBGRFormat=True)` — feed frames in
   multiples of 5, resized to **768×432**; it returns per-frame (x, y) pixel
   coords, `(0, 0)` = no ball. Sketch:
   ```python
   sys.path.insert(0, str(self.repo_path))
   import Predict
   # read video with cv2, buffer 5 frames at a time, resize to 768x432,
   # scale returned coords back to 1920x1080:  u *= 1920/768; v *= 1080/432
   # valid = (x, y) != (0, 0); conf: GridTrackNet gives grid confidences —
   # if using Predict.py as-is, set conf=1.0 for detections and rely on
   # min_confidence later once you expose the sigmoid scores.
   # frames array must be absolute frame indices + frame_offset argument.
   ```
3. Run it on a real rally clip and overlay the track (cv2.circle per frame)
   — the tennis model usually transfers *partially* to pickleball.

**Part B — fine-tune for pickleball (TRK-2):**

4. Label rally frames with the repo's `LabellingTool.py` (thousands of
   ball-visible frames across courts/lighting, per §7.3).
5. Build TFRecords with `DataGen.py`, train with
   `Train.py --tol=4` starting from `model_weights.h5`.
6. Save as `models/gridtracknet_pickleball.h5`; update config.

✅ **Done when:** on a held-out rally clip, visual overlay shows the ball
tracked through flight with no more than occasional 1–2 frame dropouts,
and dropout rate is quantified (report %, per Roadmap §11).

---

## Recipe 6 — Bounce tuning `[TUNE-2]` + bounce-vs-hit classifier `[BNC-1]`

**You need:** Recipes 2, 4, 5 done; staged bounce clips + free rallies.

1. Run the pipeline on staged ground-truth-bounce clips:
   ```bash
   python -m pickleball_phase2.pipeline camA_clip.mp4 camB_clip.mp4 --out calls.json
   ```
2. Plot s(t) (`bounce.separation_signal`) for a handful of clips. You should
   see the derivation's signature: large in flight, sharp dip at contact.
   Set `bounce.min_prominence_ft` (TUNE-2) just below the smallest true-bounce
   prominence you observe (start: 0.5 ft).
3. Now run on free rallies — you'll see FALSE minima at paddle hits (both
   projections can converge near a player). This is what BNC-1 kills.
4. Implement `classify_bounce_vs_hit()` using the §5.7 cues, computed from
   the BallTrack around the candidate frame:
   - image-space V-shape present in BOTH cameras (vshape_candidates)?
   - horizontal court velocity preserved (bounce) vs reversed (hit)?
   - ballistic (parabola) fit residual before vs after the event
   - candidate near a player detection (optional: any person detector)
   Start with a hand-tuned rule set; graduate to a small classifier
   (sklearn GradientBoosting on these features) once you have ~200 labeled
   events. Wire it into `detect_bounces()` as a filter.

✅ **Done when:** on a labeled clip set, ≥95% of true bounces kept, ≥90% of
paddle hits rejected. Log the confusion matrix in the README status table.

---

## Recipe 7 — Fusion calibration `[TUNE-3, TUNE-4]`

**You need:** bounce events with known truth. Best: taped-marker clips with
measured coordinates (§7.3). Fallback (you skipped markers): step through
slow-mo playback, eyeball each bounce against the nearest line, record
IN/OUT + rough position — cruder, still usable.

1. Run the pipeline on all ground-truth clips; collect for every event:
   xy_A, xy_B, truth, per-camera conf and reproj error (it's all in
   `LineCall.audit`).
2. Per camera, compute error vs truth. Set `fusion.reproj_err_scale_px`
   (TUNE-4) so weights ∝ how accurate each camera actually was.
3. Plot the distribution of |xy_A − xy_B| at TRUE bounces. Set
   `fusion.dispute_threshold_ft` (TUNE-3) at its 95th percentile — above
   that, the cameras genuinely disagree and arbitration kicks in.
4. Report final in/out accuracy vs truth (overall + within 2 inches of a
   line — the honest number).

✅ **Done when:** thresholds in config.yaml are data-derived (note the values
and dataset in the README), and accuracy-near-lines is documented in cm.

---

## Recipe 8 — Placement beeps `[PLC-1]` *(optional, §5.4)*

The readiness score and state machine are already implemented and tested;
only sound output is missing.

1. Laptop demo: `pip install simpleaudio`; generate a sine burst, sleep
   `beep_interval_s(score)`, repeat; one long tone on LOCKED.
2. Real deployment: it belongs in the phone web app — WebAudio API
   oscillator driven by readiness scores streamed from the server.

✅ **Done when:** walking a phone around the court audibly speeds/slows the
beep and locks with a long tone (state machine: `PlacementStateMachine`).

---

## Recipe 9 — Real-time server `[ARCH-1]` *(the next intern's project)*

Prereqs: everything above. The target architecture is documented in
`server.py` and §5.9 — cached homographies, ROI-cropped tracking, fusion
only on bounce events, A+B batched on one GPU. Suggested first milestone:
"live" processing of a pre-recorded clip pair at 60 fps with < 1 s latency,
measured and logged. Only then attach real phone streams (RTMP/WebRTC).

✅ **Done when:** end-to-end latency clap-to-call is characterized (§11).
