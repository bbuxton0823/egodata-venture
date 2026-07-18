"""QA metrics for a captured episode (visual-only pipeline).

Acceptance criteria:
  - hand visibility coverage >= 70% of frames
  - labeled-task coverage >= 60% of duration
No audio/narration — the pipeline is visual-only.
Exit code 0 = pass, 1 = fail.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

THRESHOLDS = {"hand_coverage_pct": 70.0, "task_coverage_pct": 60.0}


def qa(hands_parquet: Path, tasks_json: Path, duration_s: float) -> dict:
    df = pd.read_parquet(hands_parquet)
    frames_with_hands = df["frame"].nunique()

    tasks = json.loads(tasks_json.read_text())
    labeled = sum(t["end"] - t["start"] for t in tasks
                  if t.get("task") and t["task"] != "unlabeled")

    total_frames = max(int(df["frame"].max()) + 1, 1) if len(df) else 1
    report = {
        "duration_s": duration_s,
        "hand_coverage_pct": round(100.0 * frames_with_hands / total_frames, 2),
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
