"""Capture egocentric footage from a camera with live hand-tracking preview.

This simulates the worker's capture rig: camera pointed at hands, on-screen
skeleton confirms tracking quality while recording.

Usage:
    python capture_rig.py --output data/raw/mine.mp4 --camera 0
    python capture_rig.py --list-cameras
"""
import argparse
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"


def _make_detector(running_mode=vision.RunningMode.VIDEO):
    opts = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=running_mode,
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_tracking_confidence=0.3,
    )
    return vision.HandLandmarker.create_from_options(opts)


# 21-keypoint topology of a hand (MediaPipe convention)
HAND_CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),
                    (9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
                    (13,17),(17,18),(18,19),(19,20),(0,17)]


def _draw_hand(frame, landmarks, w, h):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
    for p in pts:
        cv2.circle(frame, p, 3, (0, 0, 255), -1)


def list_cameras(max_index: int = 6) -> list[int]:
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            found.append(i)
            cap.release()
    return found


def capture(output: Path, camera: int, show: bool = True, max_seconds: float = 0):
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open camera {camera}. Try --list-cameras.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    hands = _make_detector()

    frames = 0
    tracked = 0
    start = time.time()
    print(f"Recording {output} ({w}x{h} @ {fps:.0f}fps). Press Ctrl+C to stop.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
            frames += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int((time.time() - start) * 1000)
            res = hands.detect_for_video(mp_img, ts_ms)
            if res.hand_landmarks:
                tracked += 1
                if show:
                    for lm in res.hand_landmarks:
                        _draw_hand(frame, lm, w, h)
            if show:
                cv2.imshow("capture rig (q to stop)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            if max_seconds and time.time() - start > max_seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        writer.release()
        hands.close()
        cv2.destroyAllWindows()

    pct = 100.0 * tracked / max(frames, 1)
    print(f"Saved {frames} frames to {output}")
    print(f"Hand-track coverage: {tracked}/{frames} frames ({pct:.1f}%)")
    return frames, pct


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("data/raw/session.mp4"))
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--list-cameras", action="store_true")
    p.add_argument("--no-show", action="store_true")
    p.add_argument("--max-seconds", type=float, default=0)
    a = p.parse_args()
    if a.list_cameras:
        print("Available camera indices:", list_cameras())
    else:
        capture(a.output, a.camera, show=not a.no_show, max_seconds=a.max_seconds)
