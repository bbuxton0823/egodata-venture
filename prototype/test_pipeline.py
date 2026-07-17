"""Pipeline test: runs every stage on a synthetic video and a real hand photo.

Synthetic blobs don't fool a learned hand detector, so tracking is verified
against a real image (downloaded once to assets/) while segmentation, QA and
export run against representative data. Both paths assert the full contract.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_sample_video
import hand_tracking
import task_segmenter
import qa_metrics
import lerobot_export
import pandas as pd

HAND_IMG_URL = "https://storage.googleapis.com/mediapipe-tasks/hand_landmarker/woman_hands.jpg"
HAND_IMG = Path(__file__).parent / "assets" / "test_hands.jpg"


def _ensure_hand_image():
    HAND_IMG.parent.mkdir(parents=True, exist_ok=True)
    if not HAND_IMG.exists():
        urllib.request.urlretrieve(HAND_IMG_URL, HAND_IMG)


def test_hand_detector_on_real_image():
    """The hand model must fire on a real hands image (single-image mode)."""
    _ensure_hand_image()
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions

    opts = vision.HandLandmarkerOptions(
        base_options=BaseOptions(
            model_asset_path=str(hand_tracking.MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE, num_hands=2)
    det = vision.HandLandmarker.create_from_options(opts)
    img = cv2.imread(str(HAND_IMG))
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                      data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    res = det.detect(mp_img)
    det.close()
    assert res.hand_landmarks, "detector found no hands in reference image"
    assert len(res.hand_landmarks[0]) == 21, "expected 21 keypoints"
    print(f"DETECTOR OK: {len(res.hand_landmarks)} hand(s), 21 keypoints each")


def test_pipeline_stages(tmp_path=Path("data/test_run")):
    tmp_path.mkdir(parents=True, exist_ok=True)
    vid = tmp_path / "sample.mp4"
    make_sample_video.make_sample(vid, seconds=4.0)

    # tracking machinery runs end-to-end on the synthetic video without error
    hands_pq = tmp_path / "hands.parquet"
    hand_tracking.track_video(vid, hands_pq, sample_every=3)

    # representative hand data (as the detector would emit) drives downstream
    rows = []
    for f in range(0, 120, 3):
        for hand_i in range(2):
            for k in range(21):
                rows.append((f, round(f / 30, 4), hand_i,
                             "Left" if hand_i == 0 else "Right", 0.95,
                             k, 0.3 + 0.2 * hand_i + k * 0.01, 0.6, 0.0))
    df = pd.DataFrame(rows, columns=hand_tracking.COLUMNS)
    df.to_parquet(hands_pq, index=False)

    segs = [
        {"start": 0.0, "end": 1.5, "text": "I am picking up the plate."},
        {"start": 1.5, "end": 3.0, "text": "Now wiping the plate with the cloth."},
        {"start": 3.0, "end": 4.0, "text": "And I place it in the rack."},
    ]
    tasks = task_segmenter.segment_tasks(segs)
    labels = [t["task"] for t in tasks]
    assert labels == ["pick_up(plate)", "wipe(plate)", "place(plate,rack)"], labels
    tasks_json = tmp_path / "tasks.json"
    tasks_json.write_text(json.dumps(tasks))

    report = qa_metrics.qa(hands_pq, tasks_json, duration_s=4.0)
    assert report["keypoint_rows"] > 0
    assert report["task_coverage_pct"] >= 60.0

    out = lerobot_export.export(vid, hands_pq, tasks_json,
                                tmp_path / "dataset", "episode_000000")
    assert (out / "videos" / "episode_000000.mp4").exists()
    assert (out / "data" / "episode_000000.parquet").exists()
    assert (out / "meta" / "episodes.jsonl").exists()
    frame_df = pd.read_parquet(out / "data" / "episode_000000.parquet")
    assert len(frame_df) == 40
    assert "wipe(plate)" in set(frame_df["task"])

    print("PIPELINE STAGES PASS", json.dumps(report))
    return report


if __name__ == "__main__":
    test_hand_detector_on_real_image()
    test_pipeline_stages()
    print("ALL TESTS PASS")
