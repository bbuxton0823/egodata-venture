"""Hand tracking on egocentric video -> per-frame 2D/3D hand keypoints.

Runs MediaPipe Hands over a video and emits a Parquet file with 21 keypoints
(x, y image-normalized, z relative depth) per detected hand per frame, plus
handedness and detection confidence. This is the core enrichment artifact that
makes the footage robot-training-ready.
"""
import argparse
import json
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
import pandas as pd

COLUMNS = ["frame", "time_s", "hand_index", "handedness", "score",
           "keypoint_index", "x", "y", "z"]

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"


def track_video(video_path: Path, out_parquet: Path,
                max_frames: int = 0, sample_every: int = 1) -> pd.DataFrame:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    opts = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_tracking_confidence=0.3,
    )
    hands = vision.HandLandmarker.create_from_options(opts)

    rows = []
    frame_idx = 0
    frames_with_hands = 0
    processed = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % sample_every != 0:
            frame_idx += 1
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = hands.detect_for_video(mp_img, int(frame_idx * 1000 / fps))
        t = frame_idx / fps
        if res.hand_landmarks:
            frames_with_hands += 1
            for h_i, (lm, handed) in enumerate(
                    zip(res.hand_landmarks, res.handedness)):
                for k_i, kp in enumerate(lm):
                    rows.append((frame_idx, round(t, 4), h_i,
                                 handed[0].category_name,
                                 round(handed[0].score, 4),
                                 k_i, round(kp.x, 5), round(kp.y, 5),
                                 round(kp.z, 5)))
        processed += 1
        frame_idx += 1
        if max_frames and processed >= max_frames:
            break

    cap.release()
    hands.close()

    df = pd.DataFrame(rows, columns=COLUMNS)
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_parquet, index=False)

    stats = {
        "video": str(video_path),
        "fps": fps,
        "frames_processed": processed,
        "frames_with_hands": frames_with_hands,
        "hand_coverage_pct": round(100.0 * frames_with_hands / max(processed, 1), 2),
        "keypoint_rows": len(df),
        "parquet": str(out_parquet),
    }
    print(json.dumps(stats, indent=2))
    return df


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--max-frames", type=int, default=0)
    p.add_argument("--sample-every", type=int, default=1,
                   help="Process every Nth frame (speed vs density)")
    a = p.parse_args()
    out = a.out or Path("data/processed") / (a.video.stem + "_hands.parquet")
    track_video(a.video, out, a.max_frames, a.sample_every)
