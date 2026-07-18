"""Poll the ingest manifest for queued episodes and run the pipeline.

Visual-only pipeline — no audio, no narration, no transcription.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

UPLOAD_DIR = Path(os.getenv("EGODATA_UPLOAD_DIR", "uploads"))
MANIFEST = UPLOAD_DIR / "manifest.jsonl"
DATASET = Path(os.getenv("EGODATA_DATASET_DIR", "dataset"))
POLL_SECONDS = int(os.getenv("EGODATA_POLL_INTERVAL", "30"))


def run_pipeline(entry: dict):
    key = entry["key"]
    episode_id = entry["episode_id"]
    video = UPLOAD_DIR / key if not key.startswith("s3://") else None
    if video is None or not video.exists():
        print(f"skip {episode_id}: video not found at {key}")
        return

    print(f"pipeline start: {episode_id}")
    from hand_tracking import track_video
    from lerobot_export import export
    from qa_metrics import qa

    hands_pq = video.with_suffix(".hands.parquet")
    track_video(video, hands_pq)

    # Task labels: check for companion JSON from the app (chip-taps)
    tasks_json = video.with_suffix(".tasks.json")
    if not tasks_json.exists():
        tasks_json = video.parent / (video.stem + "_tasks.json")
    if not tasks_json.exists():
        tasks_json.write_text("[]")

    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    dur = float(r.stdout.strip() or 0)
    report = qa(hands_pq, tasks_json, dur)

    export(video, hands_pq, tasks_json, DATASET, episode_id)
    print(f"pipeline done: {episode_id} QA={'PASS' if report['pass'] else 'FAIL'}")
    return report


def main():
    print(f"pipeline poller starting — manifest {MANIFEST}, poll {POLL_SECONDS}s")
    processed = set()
    while True:
        if not MANIFEST.exists():
            time.sleep(POLL_SECONDS)
            continue
        lines = MANIFEST.read_text().strip().split("\n")
        for line in lines:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("status") != "queued":
                continue
            if entry["episode_id"] in processed:
                continue
            processed.add(entry["episode_id"])
            try:
                run_pipeline(entry)
            except Exception as e:
                print(f"pipeline err {entry['episode_id']}: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
