"""Verify the live-capture path (capture_rig) end-to-end without TCC camera access.

macOS TCC blocks camera capture from agent shells ("not authorized to capture
video"), so the real device path can't be exercised unattended. This builds a
camera-realistic POV fixture (zoom + drift simulating head motion) from the
QA'd POV still, then runs the exact MediaPipe VIDEO-mode detection loop used
by capture_rig.py against it and asserts tracking coverage.

Run once, then delete:  .venv/bin/python ../hermes-verify-capture.py
"""
import math
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision, BaseOptions

PROTO = Path(__file__).resolve().parent
STILL = PROTO / "assets" / "stills" / "j_pov_hands.png"
FIXTURE = PROTO / "data" / "verify" / "pov_fixture.mp4"
MODEL = PROTO / "models" / "hand_landmarker.task"
HAND_CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),
                    (9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
                    (13,17),(17,18),(18,19),(19,20),(0,17)]
W, H, FPS, SECONDS = 1280, 720, 30, 6

ok = True
def check(name, fn):
    global ok
    try:
        msg = fn()
        print(f"PASS {name}: {msg}")
    except Exception as e:
        ok = False
        print(f"FAIL {name}: {e}")


def make_fixture():
    img = cv2.imread(str(STILL))
    assert img is not None, f"still not found: {STILL}"
    ih, iw = img.shape[:2]
    s = max(W / iw, H / ih)
    img = cv2.resize(img, (int(iw * s) + 1, int(ih * s) + 1))
    big = cv2.resize(img, (int(W * 1.2), int(H * 1.2)))
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    wr = cv2.VideoWriter(str(FIXTURE), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    n = SECONDS * FPS
    for f in range(n):
        t = f / FPS
        z = 1.0 + 0.12 * (f / n)                      # slow push-in
        cw, ch = int(W * z), int(H * z)
        cx = (big.shape[1] - cw) // 2 + int(40 * math.sin(t * 1.6))
        cy = (big.shape[0] - ch) // 2 + int(24 * math.sin(t * 2.2 + 1))
        crop = big[cy:cy + ch, cx:cx + cw]
        wr.write(cv2.resize(crop, (W, H)))
    wr.release()
    return f"{n} frames"


def run_capture_loop():
    cap = cv2.VideoCapture(str(FIXTURE))
    assert cap.isOpened(), "cannot open fixture"
    opts = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO, num_hands=2,
        min_hand_detection_confidence=0.3, min_tracking_confidence=0.3)
    hands = vision.HandLandmarker.create_from_options(opts)
    frames, tracked, max_hands = 0, 0, 0
    start = time.time()
    overlay_out = FIXTURE.with_suffix(".overlay.mp4")
    wr = cv2.VideoWriter(str(overlay_out), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = hands.detect_for_video(mp_img, int((time.time() - start) * 1000))
        if res.hand_landmarks:
            tracked += 1
            max_hands = max(max_hands, len(res.hand_landmarks))
            for lm in res.hand_landmarks:
                pts = [(int(p.x * W), int(p.y * H)) for p in lm]
                for a, b in HAND_CONNECTIONS:
                    cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
                for p in pts:
                    cv2.circle(frame, p, 3, (0, 0, 255), -1)
        wr.write(frame)
    cap.release(); wr.release(); hands.close()
    cov = 100.0 * tracked / max(frames, 1)
    assert frames > 0 and cov >= 50, f"coverage too low: {cov:.1f}%"
    assert max_hands >= 1, "no hands detected"
    return f"{tracked}/{frames} frames tracked ({cov:.1f}%), max {max_hands} hands, overlay {overlay_out.name}"


check("fixture-built", make_fixture)
check("capture-loop-tracks-hands", run_capture_loop)
print("VERIFY OK" if ok else "VERIFY FAILED")
sys.exit(0 if ok else 1)
