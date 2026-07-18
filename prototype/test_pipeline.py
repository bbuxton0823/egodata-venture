"""End-to-end test: synthetic video → hand tracking → task labels → QA → export.

Visual-only pipeline — no audio, no narration.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_sample_video
import hand_tracking
import qa_metrics
import lerobot_export
import pandas as pd


def test_pipeline(tmp_path=Path("data/test_run")):
    tmp_path.mkdir(parents=True, exist_ok=True)
    vid = tmp_path / "sample.mp4"
    make_sample_video.make_sample(vid, seconds=4.0)

    # 1. Hand tracking on real frames
    hands_pq = tmp_path / "hands.parquet"
    hand_tracking.track_video(vid, hands_pq, sample_every=3)

    # 2. Simulated chip-tap task labels from the phone app
    rows = []
    for f in range(0, 120, 3):
        for hand_i in range(2):
            for k in range(21):
                rows.append((f, round(f / 30, 4), hand_i,
                             "Left" if hand_i == 0 else "Right", 0.95,
                             k, 0.3 + 0.2 * hand_i + k * 0.01, 0.6, 0.0))
    df = pd.DataFrame(rows, columns=hand_tracking.COLUMNS)
    df.to_parquet(hands_pq, index=False)

    task_list = [
        {"start": 0.0, "end": 1.5, "task": "wipe(plate)",
         "source": "chip_tap"},
        {"start": 1.5, "end": 4.0, "task": "wipe(surface)",
         "source": "chip_tap"},
    ]
    tasks_json = tmp_path / "tasks.json"
    tasks_json.write_text(json.dumps(task_list))

    # 3. QA gate (2 metrics, no narration)
    report = qa_metrics.qa(hands_pq, tasks_json, duration_s=4.0)
    assert report["keypoint_rows"] > 0
    assert report["task_coverage_pct"] >= 60.0

    # 4. LeRobot export
    out = lerobot_export.export(vid, hands_pq, tasks_json,
                                tmp_path / "dataset", "episode_000000")
    assert (out / "videos" / "episode_000000.mp4").exists()
    assert (out / "data" / "episode_000000.parquet").exists()
    assert (out / "meta" / "episodes.jsonl").exists()
    frame_df = pd.read_parquet(out / "data" / "episode_000000.parquet")
    assert len(frame_df) == 40
    assert "wipe(plate)" in set(frame_df["task"])

    print("PIPELINE OK", json.dumps(report))
    return report


if __name__ == "__main__":
    test_pipeline()
    print("ALL TESTS PASS")
