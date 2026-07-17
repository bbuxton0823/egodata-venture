"""Render an annotated preview: hand skeleton + task label burned onto video.

This is the visual proof-of-quality artifact for buyers and workers.
"""
import argparse
import json
from pathlib import Path

import cv2
import pandas as pd

CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),
               (10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(17,18),
               (18,19),(19,20),(0,17)]


def render(video: Path, hands: Path, tasks: Path, out: Path,
           max_seconds: float = 0):
    df = pd.read_parquet(hands)
    task_list = json.loads(tasks.read_text())
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (w, h))
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = idx / fps
        sub = df[df["frame"] == idx]
        for hand_i in sub["hand_index"].unique():
            hd = sub[sub["hand_index"] == hand_i].sort_values("keypoint_index")
            pts = [(int(r.x * w), int(r.y * h)) for r in hd.itertuples()]
            for a_, b_ in CONNECTIONS:
                if a_ < len(pts) and b_ < len(pts):
                    cv2.line(frame, pts[a_], pts[b_], (0, 255, 0), 2)
            for p_ in pts:
                cv2.circle(frame, p_, 3, (0, 0, 255), -1)
        label = next((e["task"] for e in task_list if e["start"] <= t < e["end"]), "")
        if label:
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1.1, (255, 255, 255), 3, cv2.LINE_AA)
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1.1, (0, 200, 0), 2, cv2.LINE_AA)
        writer.write(frame)
        idx += 1
        if max_seconds and t > max_seconds:
            break
    cap.release()
    writer.release()
    print(f"wrote {out} ({idx} frames)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--hands", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("data/processed/annotated.mp4"))
    p.add_argument("--max-seconds", type=float, default=0)
    a = p.parse_args()
    render(a.video, a.hands, a.tasks, a.out, a.max_seconds)
