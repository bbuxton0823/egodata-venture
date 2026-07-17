"""Generate a synthetic egocentric sample video with scripted hand motion.

Used by tests and CI so the pipeline is verifiable without a human operator.
Draws two moving 'hands' (21-keypoint blobs) performing a wipe motion over a
'plate', with timestamps embedded. Not for training value — only for
pipeline validation.
"""
import argparse
import math
from pathlib import Path

import cv2
import numpy as np


def hand_blob(frame, cx, cy, angle, scale=1.0, color=(180, 160, 140)):
    """Draw a crude hand: palm ellipse + 5 finger lines."""
    cv2.ellipse(frame, (int(cx), int(cy)),
                (int(28 * scale), int(20 * scale)), math.degrees(angle),
                0, 360, color, -1)
    for i in range(5):
        spread = (i - 2) * 0.28
        a = angle - math.pi / 2 + spread
        length = (34 - abs(i - 2) * 5) * scale
        x2 = cx + math.cos(a) * length
        y2 = cy + math.sin(a) * length
        cv2.line(frame, (int(cx), int(cy)), (int(x2), int(y2)), color,
                 int(9 * scale), cv2.LINE_AA)
        cv2.circle(frame, (int(x2), int(y2)), int(5 * scale), color, -1)


def make_sample(out: Path, seconds: float = 8.0, fps: int = 30,
                size=(1280, 720)):
    w, h = size
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, size)
    n = int(seconds * fps)
    for i in range(n):
        t = i / fps
        # kitchen-ish background: counter plane + plate
        frame = np.full((h, w, 3), (90, 110, 130), np.uint8)  # wall
        cv2.rectangle(frame, (0, int(h * 0.45)), (w, h), (150, 120, 90), -1)
        # plate
        px, py = w // 2, int(h * 0.68)
        cv2.ellipse(frame, (px, py), (170, 90), 0, 0, 360, (235, 235, 240), -1)
        cv2.ellipse(frame, (px, py), (130, 65), 0, 0, 360, (215, 215, 222), -1)
        # hands: wipe circular motion around plate center
        a1 = t * 2.2
        hx1 = px + math.cos(a1) * 120
        hy1 = py + math.sin(a1) * 55 - 40
        a2 = t * 2.2 + 1.9
        hx2 = px + math.cos(a2) * 150
        hy2 = py + math.sin(a2) * 70 - 30
        hand_blob(frame, hx2, hy2, a2 + 0.6, scale=1.0)
        hand_blob(frame, hx1, hy1, a1 - 0.4, scale=1.1)
        # timestamp text (also useful for sync checks)
        cv2.putText(frame, f"t={t:05.2f}", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()
    print(f"wrote {out} ({n} frames @ {fps}fps)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("data/raw/sample.mp4"))
    p.add_argument("--seconds", type=float, default=8.0)
    a = p.parse_args()
    make_sample(a.out, a.seconds)
