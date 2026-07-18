# Egocentric Home-Task Data — Phase 0 Prototype

Working prototype of the capture + enrichment pipeline for the egocentric
home-task training-data business (see `../OUTLINE.md`).

A worker wears a head/hat camera pointed at their hands and narrates while
doing household tasks. This repo turns that raw footage into an enriched,
QA-gated, LeRobot-style dataset episode:

```
raw video ──► hand tracking (21 kps × 2 hands) ──► narration transcript (Whisper)
          ──► task labels (taxonomy) ──► QA gate ──► LeRobot-style export
```

## Contents

| file | role |
|---|---|
| `capture_rig.py` | record from any camera w/ live hand-skeleton preview |
| `hand_tracking.py` | video → per-frame 2D/3D hand keypoints (Parquet) |
| `narration_transcribe.py` | audio → time-aligned transcript (faster-whisper) |
| `task_segmenter.py` | transcript → time-coded task labels (taxonomy rules) |
| `qa_metrics.py` | acceptance gate: hand/narration/label coverage |
| `lerobot_export.py` | episode → `videos/ + data/ + meta/` LeRobot layout |
| `pipeline.py` | all five stages, one command |
| `make_demo_video.py` | renders the original narrated demo (assets/demo/egodata_demo.mp4) |
| `make_demo_video_multi.py` | renders the multi-angle demo (assets/demo/egodata_demo_multi.mp4) |
| `test_pipeline.py` | end-to-end verification (real detector + stage contracts) |

## Setup

```bash
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install mediapipe opencv-python-headless numpy pandas pyarrow faster-whisper
# hand model (one-time):
mkdir -p models && curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```

## Verify

```bash
python test_pipeline.py        # detector + all pipeline stages
```

Expected tail: `DETECTOR OK: 2 hand(s), 21 keypoints each` … `ALL TESTS PASS`.

## Run on real footage

```bash
python capture_rig.py --list-cameras
python capture_rig.py --output data/raw/kitchen.mp4 --camera 0   # q to stop
python pipeline.py --video data/raw/kitchen.mp4 --episode episode_000001
```

Output: `dataset/` with `videos/episode_000001.mp4`,
`data/episode_000001.parquet` (per-frame hand state + task label), and
`meta/episodes.jsonl` + `meta/tasks.jsonl`. QA report prints PASS/FAIL with
coverage percentages (thresholds in `qa_metrics.py`).

## Demo videos

**Multi-angle** (`assets/demo/egodata_demo_multi.mp4`, 52 s, 1080p): front,
side, high, and rig close-up angles of a worker wearing the head camera,
then a REAL MediaPipe hand-skeleton capture clip proving the live pipeline
tracks hands. Rebuild with:

```bash
python hermes-verify-capture.py   # builds data/verify/pov_fixture.overlay.mp4
python make_demo_video_multi.py
```

**Original** (`assets/demo/egodata_demo.mp4`, 40 s, 1080p): narrated concept
walkthrough — capture rig → POV with real hand-skeleton overlay → QA gate →
export format. Rebuild with `python make_demo_video.py`.

Stills in `assets/stills/` are AI-generated placeholders for illustration, not
captured data; the hand skeletons in the POV segments are real MediaPipe
detections on those frames.

## Live camera capture (macOS TCC caveat)

`capture_rig.py` opens the first available camera and draws the hand skeleton
in real time. On macOS the terminal app must be granted Camera access under
System Settings → Privacy & Security → Camera, otherwise OpenCV prints
"not authorized to capture video" and returns zero devices. The automated
verification path (`test_pipeline.py` + `hermes-verify-capture.py`) exercises
the same detection loop on a pre-recorded fixture so CI and unattended runs
still verify the full pipeline.

## Prototype scope (what's deliberately thin)

- Task labeling is keyword rules; production swaps in a model fine-tuned on
  Ego4D/EPIC-KITCHENS with human QA review.
- No face-blur/PII pipeline yet (required before any non-consented footage).
- LeRobot export matches the layout conventions; validate against a specific
  buyer's dataloader version before delivery.
