#!/usr/bin/env python3
"""Desktop companion app — visual-only capture workflow.

Records video from camera, runs hand tracking, applies task labels
(from in-app chip-taps), QA gate, and LeRobot export.
No audio, no narration, no transcription.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROTO = Path(__file__).parent.parent / "prototype"
sys.path.insert(0, str(PROTO))

from hand_tracking import track_video
from lerobot_export import export
from qa_metrics import qa


def main():
    p = argparse.ArgumentParser(description="EgoData Desktop Companion")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--output", type=Path, default=Path("captures/session.mp4"))
    p.add_argument("--episode", default="episode_000001")
    p.add_argument("--max-seconds", type=float, default=0)
    p.add_argument("--no-preview", action="store_true")
    args = p.parse_args()

    print("=" * 50)
    print("DATA HAT — Desktop Companion (visual-only)")
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

    print("\n--- HAND TRACKING ---")
    hands_pq = args.output.with_suffix(".hands.parquet")
    df = track_video(args.output, hands_pq)
    print(f"  {len(df['frame'].unique())} frames with hands, "
          f"{len(df)} keypoint rows")

    print("\n--- TASK LABELS ---")
    tasks_json = args.output.with_suffix(".tasks.json")
    if not tasks_json.exists():
        tasks_json = args.output.parent / (args.output.stem + "_tasks.json")
    if not tasks_json.exists():
        print("  no tasks.json — writing empty (add via app chip-taps)")
        tasks_json.write_text("[]")

    print("\n--- QA GATE ---")
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                        "format=duration", "-of", "csv=p=0",
                        str(args.output)], capture_output=True, text=True)
    dur = float(r.stdout.strip() or 0)
    report = qa(hands_pq, tasks_json, dur)
    print(json.dumps(report, indent=2))
    print(f"\nQA {'PASS' if report['pass'] else 'FAIL'}")

    print("\n--- LeRobot EXPORT ---")
    dataset = Path("dataset")
    export(args.output, hands_pq, tasks_json, dataset, args.episode)
    print(f"  episode '{args.episode}' → {dataset}/")


if __name__ == "__main__":
    main()
