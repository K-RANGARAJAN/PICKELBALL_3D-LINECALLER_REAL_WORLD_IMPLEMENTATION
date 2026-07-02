# data/

Drop the real-world captures here (kept out of git — see .gitignore).

Expected layout (matches the §7.4 naming scheme):

```
data/
  raw/                      YYYY-MM-DD_S<session>_cam<A|B|K>_clip<NNN>.mp4
  master_log.csv            one row per clip (Appendix D schema)
  frames/                   extracted frames for keypoint annotation (Recipe 2)
  labels/                   YOLO-pose keypoint labels (Recipe 2)
  tracker_labels/           GridTrackNet labels (Recipe 5)
calib/
  intrinsics/               camA.yaml, camB.yaml, camK.yaml (Recipe 1)
models/                     court_keypoints_realworld.pt, gridtracknet_pickleball.h5
third_party/GridTrackNet/   clone of the GridTrackNet repo (Recipe 5)
```

Master-log columns (Appendix D): filename, date, session, camera, fps,
resolution, content_type, sync_event, occluded_camera, gt_markers_present,
gt_marker_coords, notes.
