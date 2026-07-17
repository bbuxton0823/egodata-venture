#!/usr/bin/env python3
"""Desktop companion app — runs the same capture workflow as the phone app.

Uses the prototype pipeline modules. This is what you run on a Mac to test
the Data Hat rig with a USB webcam or built-in camera before deploying
the phone app to workers.
"""
import argparse
import json
import sys
import time
from pathlib import Path

# Point at the prototype pipeline — these are the same modules the cloud
# processing pipeline uses.
PROTO = Path(__file__).parent.parent / "prototype"
sys.path.insert(0, str(PROTO))

from hand_tracking import track_video
from narration_transcribe import transcribe
from task_segmenter import segment_tasks
from lerobot_export import export
from qa_metrics import qa


def main():
    p = argparse.ArgumentParser(description="EgoData Desktop Companion")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("captures/session.mp4"))
    p.add_argument("--episode", default="episode_000001")
    p.add_argument("--max-seconds", type=float, default=0,
                   help="0 = record until stopped")
    p.add_argument("--no-preview", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    # Step 1: Record
    print("=" * 50)
    print("DATA HAT — Desktop Companion")
    print("=" * 50)
    print(f"Camera: {args.camera}  |  Output: {args.output}")
    print("Press Ctrl+C to stop recording.\n")

    import capture_rig
    frames, hand_pct = capture_rig.capture(
        args.output, args.camera, show=not args.no_preview,
        max_seconds=args.max_seconds,
    )

    if frames == 0:
        print("No frames captured — aborting.")
        return

    # Step 2: Hand tracking
    print("\n--- HAND TRACKING ---")
    hands_pq = args.output.with_suffix(".hands.parquet")
    df = track_video(args.output, hands_pq)
    print(json.dumps({"frames_with_hands": len(df["frame"].unique()),
                       "keypoint_rows": len(df)}, indent=2))

    # Step 3: Narration (extract audio + transcribe)
    print("\n--- NARRATION ---")
    import subprocess
    import tempfile
    audio = args.output.with_suffix(".wav")
    subprocess.run(["ffmpeg", "-y", "-i", str(args.output), "-vn", "-ac", "1",
                    "-ar", "16000", str(audio)], check=True, capture_output=True)
    if audio.stat().st_size > 800:  # not silent
        segs = transcribe(audio)
        print(f"  transcribed {len(segs)} segments")
    else:
        segs = []
        print("  audio silent — no transcription")

    # Step 4: Task labels
    print("\n--- TASK LABELS ---")
    tasks = segment_tasks(segs) if segs else []
    tasks_json = args.output.with_suffix(".tasks.json")
    tasks_json.write_text(json.dumps(tasks, indent=2))
    print(f"  {len(tasks)} task episodes")

    # Step 5: QA
    print("\n--- QA GATE ---")
    import subprocess as sp
    r = sp.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(args.output)], capture_output=True, text=True)
    dur = float(r.stdout.strip() or 0)
    report = qa(hands_pq, tasks_json, dur)
    print(json.dumps(report, indent=2))
    print(f"\nQA {'PASS' if report['pass'] else 'FAIL'}")

    # Step 6: Export
    print("\n--- LeRobot EXPORT ---")
    dataset = Path("dataset")
    export(args.output, hands_pq, tasks_json, dataset, args.episode)
    print(f"  episode '{args.episode}' → {dataset}/")


if __name__ == "__main__":
    main()
