"""QA metrics for a captured episode.

Computes the acceptance criteria from the business plan:
  - hand visibility coverage >= 70% of frames
  - narration coverage >= 50% of duration
  - labeled-task coverage >= 60% of duration
Exit code 0 = pass, 1 = fail (usable in CI).
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

THRESHOLDS = {"hand_coverage_pct": 70.0, "narration_coverage_pct": 50.0,
              "task_coverage_pct": 60.0}


def qa(hands_parquet: Path, tasks_json: Path, duration_s: float) -> dict:
    df = pd.read_parquet(hands_parquet)
    frames_with_hands = df["frame"].nunique()

    tasks = json.loads(tasks_json.read_text())
    narrated = sum(t["end"] - t["start"] for t in tasks if t["narration"].strip())
    labeled = sum(t["end"] - t["start"] for t in tasks if t["task"] != "idle/other")

    # frames_with_hands is relative to processed frames; duration in seconds
    # assume ~constant fps: total frames ~= duration * fps inferred from max frame
    total_frames = max(int(df["frame"].max()) + 1, 1) if len(df) else 1
    report = {
        "duration_s": duration_s,
        "hand_coverage_pct": round(100.0 * frames_with_hands / total_frames, 2),
        "narration_coverage_pct": round(100.0 * narrated / max(duration_s, 0.01), 2),
        "task_coverage_pct": round(100.0 * labeled / max(duration_s, 0.01), 2),
        "episodes": len(tasks),
        "keypoint_rows": len(df),
    }
    report["pass"] = all(report[k] >= v for k, v in THRESHOLDS.items())
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--hands", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--duration", type=float, required=True)
    a = p.parse_args()
    report = qa(a.hands, a.tasks, a.duration)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["pass"] else 1)
