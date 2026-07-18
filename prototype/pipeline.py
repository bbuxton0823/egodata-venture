"""End-to-end pipeline: video + task labels → enriched LeRobot episode.

Visual-only — no audio, no narration, no transcription.
Task labels come from the worker's in-app chip-taps (tasks.json).

    python pipeline.py --video X.mp4 --tasks X_tasks.json --episode NAME

Steps: hand tracking → task labels → QA → LeRobot export.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hand_tracking
import qa_metrics
import lerobot_export


def video_duration(video: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def run(video: Path, tasks: Path | None, episode: str,
        dataset_dir: Path = Path("dataset")):
    proc = Path("data/processed")
    proc.mkdir(parents=True, exist_ok=True)
    stem = video.stem

    print("== 1/4 hand tracking ==")
    hands_pq = proc / f"{stem}_hands.parquet"
    hand_tracking.track_video(video, hands_pq)

    print("== 2/4 task labels ==")
    if tasks and tasks.exists():
        task_list = json.loads(tasks.read_text())
    else:
        task_list = []
    tasks_json = proc / f"{stem}_tasks.json"
    tasks_json.write_text(json.dumps(task_list, indent=2))
    print(f"  {len(task_list)} task episodes from metadata")

    print("== 3/4 QA ==")
    duration = video_duration(video)
    report = qa_metrics.qa(hands_pq, tasks_json, duration)
    print(json.dumps(report, indent=2))

    print("== 4/4 LeRobot export ==")
    lerobot_export.export(video, hands_pq, tasks_json, dataset_dir, episode)

    print(f"\nQA {'PASS' if report['pass'] else 'FAIL'} — episode '{episode}' complete")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--tasks", type=Path, default=None,
                   help="JSON file with timestamped task-label chips from the app")
    p.add_argument("--episode", default="episode_000000")
    p.add_argument("--dataset", type=Path, default=Path("dataset"))
    a = p.parse_args()
    run(a.video, a.tasks, a.episode, a.dataset)
