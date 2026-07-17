"""Export an episode to a LeRobot-style dataset layout.

Creates:
    <out>/
      videos/<episode>.mp4
      data/<episode>.parquet        (per-frame table, LeRobot convention)
      meta/episodes.jsonl           (episode-level manifest)
      meta/tasks.jsonl              (task label manifest)

The per-frame parquet follows the LeRobot pattern: one row per timestep with
observation + annotation columns, so a training dataloader can stream it.
"""
import argparse
import json
from pathlib import Path

import pandas as pd


def export(video: Path, hands: Path, tasks: Path, out_dir: Path,
           episode_name: str, fps: float = 30.0):
    out_dir = Path(out_dir)
    (out_dir / "videos").mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    (out_dir / "meta").mkdir(parents=True, exist_ok=True)

    hands_df = pd.read_parquet(hands)
    task_list = json.loads(tasks.read_text())

    # per-frame table: aggregate both hands' keypoints into a flat vector
    frames = sorted(hands_df["frame"].unique()) if len(hands_df) else []
    rows = []
    for f in frames:
        sub = hands_df[hands_df["frame"] == f]
        t = float(sub["time_s"].iloc[0])
        vec = [0.0] * (2 * 21 * 3)
        for _, r in sub.iterrows():
            base = int(r["hand_index"]) * 63 + int(r["keypoint_index"]) * 3
            if base + 2 < len(vec):
                vec[base:base + 3] = [r["x"], r["y"], r["z"]]
        task = next((e["task"] for e in task_list if e["start"] <= t < e["end"]),
                    "unlabeled")
        rows.append({"frame_index": int(f), "timestamp": t,
                     "observation.state": vec, "task": task})
    frame_df = pd.DataFrame(rows)

    # copy video
    import shutil
    vid_out = out_dir / "videos" / f"{episode_name}.mp4"
    shutil.copy(video, vid_out)

    frame_df.to_parquet(out_dir / "data" / f"{episode_name}.parquet", index=False)

    with open(out_dir / "meta" / "episodes.jsonl", "a") as f:
        f.write(json.dumps({
            "episode_index": episode_name,
            "video_path": f"videos/{episode_name}.mp4",
            "data_path": f"data/{episode_name}.parquet",
            "fps": fps, "num_frames": len(frame_df),
            "duration_s": round(frame_df["timestamp"].max(), 2) if len(frame_df) else 0,
        }) + "\n")
    with open(out_dir / "meta" / "tasks.jsonl", "a") as f:
        for e in task_list:
            f.write(json.dumps({"episode_index": episode_name, **e}) + "\n")

    print(f"exported episode '{episode_name}' -> {out_dir}")
    print(f"  frames={len(frame_df)}  video={vid_out.name}")
    return out_dir


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--hands", type=Path, required=True)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("dataset"))
    p.add_argument("--episode", default="episode_000000")
    p.add_argument("--fps", type=float, default=30.0)
    a = p.parse_args()
    export(a.video, a.hands, a.tasks, a.out, a.episode, a.fps)
