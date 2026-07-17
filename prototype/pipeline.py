"""End-to-end pipeline: video + narration audio -> enriched LeRobot episode.

    python pipeline.py --video X.mp4 [--audio Y.m4a] [--episode NAME]

Steps: hand tracking -> transcription -> task labeling -> QA -> export.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hand_tracking
import narration_transcribe
import task_segmenter
import qa_metrics
import lerobot_export


def extract_audio(video: Path, out: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         str(out)], check=True, capture_output=True)
    return out


def video_duration(video: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def run(video: Path, audio: Path | None, episode: str,
        dataset_dir: Path = Path("dataset"), whisper_model: str = "base"):
    proc = Path("data/processed")
    proc.mkdir(parents=True, exist_ok=True)
    stem = video.stem

    print("== 1/5 hand tracking ==")
    hands_pq = proc / f"{stem}_hands.parquet"
    hand_tracking.track_video(video, hands_pq)

    print("== 2/5 narration transcription ==")
    if audio is None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tmp = Path(tf.name)
        try:
            extract_audio(video, tmp)
            segs = narration_transcribe.transcribe(tmp, whisper_model)
        finally:
            tmp.unlink(missing_ok=True)
    else:
        segs = narration_transcribe.transcribe(audio, whisper_model)
    transcript_json = proc / f"{stem}_transcript.json"
    transcript_json.write_text(json.dumps(segs, indent=2))

    print("== 3/5 task labeling ==")
    tasks = task_segmenter.segment_tasks(segs)
    tasks_json = proc / f"{stem}_tasks.json"
    tasks_json.write_text(json.dumps(tasks, indent=2))

    print("== 4/5 QA ==")
    duration = video_duration(video)
    report = qa_metrics.qa(hands_pq, tasks_json, duration)
    print(json.dumps(report, indent=2))

    print("== 5/5 LeRobot export ==")
    lerobot_export.export(video, hands_pq, tasks_json, dataset_dir, episode)

    print(f"\nQA {'PASS' if report['pass'] else 'FAIL'} — episode '{episode}' complete")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--audio", type=Path, default=None)
    p.add_argument("--episode", default="episode_000000")
    p.add_argument("--dataset", type=Path, default=Path("dataset"))
    p.add_argument("--whisper-model", default="base")
    a = p.parse_args()
    run(a.video, a.audio, a.episode, a.dataset, a.whisper_model)
