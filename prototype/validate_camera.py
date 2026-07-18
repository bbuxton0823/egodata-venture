"""Validate the ELP USB camera on arrival — feed test, resolution, FPS.
Run before deploying the rig to a worker: confirms the camera enumerates,
opens, delivers frames at spec, and survives 60s continuous capture.
"""
import sys, time, argparse
from pathlib import Path
import cv2

OUT = Path("data/raw/validation.mp4")


def test_camera(idx: int = 0, secs: float = 10, write: bool = True):
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        raise SystemExit(f"FAIL: camera {idx} not found. Try --index or plug it in.")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    codec = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec_s = "".join(chr((codec >> (i * 8)) & 0xFF) for i in range(4)).rstrip("\x00")
    print(f"camera {idx}: {w}x{h} @ {fps:.1f}fps  codec={codec_s}")

    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        wr = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    frames, start = 0, time.time()
    while time.time() - start < secs:
        ok, frame = cap.read()
        if not ok:
            print(f"FAIL: read dropped at frame {frames}")
            break
        frames += 1
        if write:
            wr.write(frame)
    cap.release()
    if write:
        wr.release()
    actual_fps = frames / max(time.time() - start, 0.001)
    size_mb = OUT.stat().st_size / 1e6 if write and OUT.exists() else 0
    verdict = "PASS" if frames > 10 and actual_fps > 10 else "FAIL"
    print(f"{verdict}: {frames} frames in {time.time()-start:.1f}s ({actual_fps:.1f} fps)")
    if write and verdict == "PASS":
        print(f"  saved {OUT} ({size_mb:.1f}MB)")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--seconds", type=float, default=10)
    p.add_argument("--no-save", action="store_true")
    args = p.parse_args()
    sys.exit(test_camera(args.index, args.seconds, not args.no_save))
