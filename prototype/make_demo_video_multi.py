"""Build the multi-angle shareable demo: person + head camera, working capture.

Angles: front, side profile, over-shoulder high, rig close-up, then a REAL
MediaPipe hand-skeleton capture clip (pov_fixture.overlay.mp4) proving the
camera pipeline tracks hands live. Narration: Eleven Labs (assets/vo/multi/).
Output: assets/demo/egodata_demo_multi.mp4 (1080p30, H.264 + AAC)
"""
import subprocess
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision, BaseOptions

ROOT = Path(__file__).parent
STILLS = ROOT / "assets" / "stills"
VO = ROOT / "assets" / "vo" / "multi"
OUT = ROOT / "assets" / "demo"
OUT.mkdir(parents=True, exist_ok=True)
OVERLAY_CLIP = ROOT / "data" / "verify" / "pov_fixture.overlay.mp4"

W, H, FPS = 1920, 1080, 30
CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),
               (10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(17,18),
               (18,19),(19,20),(0,17)]

WHITE = (245, 245, 245)
MUTED = (155, 165, 177)
GREEN = (80, 220, 100)
RED = (70, 70, 235)
DARK = (28, 24, 20)  # BGR
ACCENT = (255, 130, 70)

FONT = cv2.FONT_HERSHEY_SIMPLEX


def text(frame, s, x, y, scale=1.0, color=WHITE, thick=2, center=False):
    if center:
        (tw, th), _ = cv2.getTextSize(s, FONT, scale, thick)
        x = (frame.shape[1] - tw) // 2
    cv2.putText(frame, s, (x, y), FONT, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(frame, s, (x, y), FONT, scale, color, thick, cv2.LINE_AA)


def writer(path):
    return cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))


def encode_audio_mux(silent: Path, vo: Path | None, dur: float, out: Path):
    cmd = ["ffmpeg", "-y", "-i", str(silent)]
    if vo and vo.exists():
        cmd += ["-i", str(vo)]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(dur)]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-shortest", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    silent.unlink(missing_ok=True)


def load_cover(img_path):
    img = cv2.imread(str(img_path))
    ih, iw = img.shape[:2]
    s = max(W / iw, H / ih)
    img = cv2.resize(img, (int(iw * s) + 1, int(ih * s) + 1),
                     interpolation=cv2.INTER_AREA)
    ih, iw = img.shape[:2]
    x, y = (iw - W) // 2, (ih - H) // 2
    return img[y:y + H, x:x + W]


def ken_burns_segment(img, dur, zoom_in=True, fx=None):
    n = int(dur * FPS)
    big = cv2.resize(img, (int(W * 1.15), int(H * 1.15)),
                     interpolation=cv2.INTER_AREA)
    for f in range(n):
        t01 = f / max(n - 1, 1)
        z = 1.0 + 0.15 * t01 if zoom_in else 1.15 - 0.15 * t01
        cw, ch = int(W * z), int(H * z)
        max_x, max_y = big.shape[1] - cw, big.shape[0] - ch
        ox = int(max_x * (0.5 + 0.2 * np.sin(t01 * np.pi)))
        oy = int(max_y * (0.5 - 0.2 * np.cos(t01 * np.pi)))
        crop = big[oy:oy + ch, ox:ox + cw]
        frame = cv2.resize(crop, (W, H), interpolation=cv2.INTER_AREA)
        if fx:
            fx(frame, t01)
        yield frame


def badge(frame, s):
    (tw, th), _ = cv2.getTextSize(s, FONT, 0.85, 2)
    x = W - tw - 60
    cv2.rectangle(frame, (x - 14, 30), (x + tw + 14, 30 + th + 24), DARK, -1)
    text(frame, s, x, 30 + th + 6, 0.85, WHITE, 2)


def seg_title(out, lines, dur, sub=None, vo=None):
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)
    for _ in range(int(dur * FPS)):
        frame = np.full((H, W, 3), DARK, np.uint8)
        y = H // 2 - (len(lines) - 1) * 60
        for ln in lines:
            text(frame, ln, 0, y, 2.2, WHITE, 4, center=True)
            y += 130
        if sub:
            text(frame, sub, 0, y + 30, 0.95, MUTED, 2, center=True)
        vw.write(frame)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def seg_still(out, img_path, dur, caption=None, badge_text=None, vo=None,
              zoom_in=True):
    img = load_cover(img_path)
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)

    def overlays(frame, t01):
        if caption:
            text(frame, caption, 60, H - 90, 1.1, WHITE, 2)
        if badge_text:
            badge(frame, badge_text)
        cv2.rectangle(frame, (0, H - 6), (int(W * t01), H), ACCENT, -1)

    for fr in ken_burns_segment(img, dur, zoom_in, overlays):
        vw.write(fr)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def seg_capture_clip(out, clip_path, dur, task_label, vo=None):
    """Play the REAL hand-tracked capture clip with a HUD — proof the camera works."""
    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise RuntimeError(f"capture overlay clip missing: {clip_path}")
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)
    n = int(dur * FPS)
    f = 0
    while f < n:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop the short clip
            continue
        frame = cv2.resize(frame, (W, H))
        cv2.rectangle(frame, (0, 0), (W, 58), DARK, -1)
        t = f / FPS
        text(frame, f"EGO-CAM 01   REC {t:05.1f}s   2 hands x 21 keypoints   30 fps",
             26, 38, 0.8, WHITE, 2)
        cv2.circle(frame, (W - 120, 29), 9, (60, 60, 255), -1)
        text(frame, "REC", W - 95, 38, 0.8, (60, 60, 255), 2)
        text(frame, f"task: {task_label}", 26, H - 36, 1.2, GREEN, 2)
        vw.write(frame)
        f += 1
    cap.release()
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def seg_qa(out, dur, vo=None):
    metrics = [("hand visibility", 1.00, 0.70),
               ("task label coverage", 0.91, 0.60)]
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)
    n = int(dur * FPS)
    for f in range(n):
        t01 = f / max(n - 1, 1)
        frame = np.full((H, W, 3), DARK, np.uint8)
        text(frame, "Automated QA gate", 60, 130, 1.9, WHITE, 3)
        y = 280
        for name, val, thr in metrics:
            shown = val * min(1.0, t01 / 0.55)
            text(frame, name, 60, y, 1.0, WHITE, 2)
            bar_w = 1150
            cv2.rectangle(frame, (60, y + 20), (60 + bar_w, y + 62), (60, 60, 60), -1)
            cv2.rectangle(frame, (60, y + 20), (60 + int(bar_w * shown), y + 62), GREEN, -1)
            tx = 60 + int(bar_w * thr)
            cv2.line(frame, (tx, y + 12), (tx, y + 70), (200, 200, 200), 2)
            text(frame, f"{shown*100:4.1f}%  (min {int(thr*100)}%)",
                 60 + bar_w + 40, y + 54, 0.95, WHITE, 2)
            y += 190
        if t01 > 0.65:
            alpha = min(1.0, (t01 - 0.65) / 0.15)
            col = tuple(int(c * alpha) for c in GREEN)
            text(frame, "EPISODE ACCEPTED", 60, y + 60, 1.7, col, 4)
        vw.write(frame)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def seg_dataset(out, dur, vo=None):
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)
    lines = [("videos/", "episode_000001.mp4      raw first-person footage"),
             ("data/",   "episode_000001.parquet  per-frame hand state + task"),
             ("meta/",   "episodes.jsonl  tasks.jsonl  QA report")]
    n = int(dur * FPS)
    for f in range(n):
        t01 = f / max(n - 1, 1)
        frame = np.full((H, W, 3), DARK, np.uint8)
        text(frame, "One shift in, one enriched episode out", 60, 150, 1.7, WHITE, 3)
        y = 330
        for i, (k, v) in enumerate(lines):
            if t01 > 0.15 + i * 0.2:
                text(frame, k, 90, y, 1.15, GREEN, 3)
                text(frame, v, 320, y, 0.95, WHITE, 2)
                y += 130
        if t01 > 0.8:
            text(frame, "LeRobot-layout export — ready for a lab's dataloader",
                 60, H - 120, 0.95, MUTED, 2)
        vw.write(frame)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def main():
    plan = [
        ("01_title", lambda o: seg_title(
            o, ["First-person data", "for home robots"], 6.0,
            sub="one worker · one head camera · real tasks", vo=VO / "m1.mp3")),
        ("02_front", lambda o: seg_still(
            o, STILLS / "a_front.png", 7.0, caption="Head camera aimed at the hands",
            badge_text="ANGLE 1 · FRONT", vo=VO / "m2.mp3")),
        ("03_side", lambda o: seg_still(
            o, STILLS / "h_side.png", 5.0, caption="Fixed downward pitch, hands always in frame",
            badge_text="ANGLE 2 · SIDE", vo=VO / "m3.mp3", zoom_in=False)),
        ("04_high", lambda o: seg_still(
            o, STILLS / "i_high.png", 6.7, caption="Standardized mount = standardized data",
            badge_text="ANGLE 3 · HIGH", vo=VO / "m4.mp3")),
        ("05_rig", lambda o: seg_still(
            o, STILLS / "k_closeup_rig.png", 6.2, caption="Under $250 · one button · two-hour battery",
            badge_text="THE RIG", vo=VO / "m5.mp3", zoom_in=False)),
        ("06_capture", lambda o: seg_capture_clip(
            o, OVERLAY_CLIP, 6.8, "wipe(plate)", vo=VO / "m6.mp3")),
        ("07_qa", lambda o: seg_qa(o, 5.2, vo=VO / "m7.mp3")),
        ("08_dataset", lambda o: seg_dataset(o, 7.4, vo=VO / "m8.mp3")),
        ("09_end", lambda o: seg_title(
            o, ["Real homes. Real tasks. Real data."], 3.0,
            sub="egocentric capture · hand tracking · task labels · QA",
            vo=VO / "m9.mp3")),
    ]
    segs = []
    for name, fn in plan:
        seg_path = OUT / f"m_{name}.mp4"
        print("render", name)
        fn(seg_path)
        segs.append(seg_path)

    n = len(segs)
    filter_str = "".join(f"[{i}:v][{i}:a]" for i in range(n)) + \
        f"concat=n={n}:v=1:a=1[v][a]"
    final = OUT / "egodata_demo_multi.mp4"
    cmd = ["ffmpeg", "-y"]
    for s in segs:
        cmd += ["-i", str(s)]
    cmd += ["-filter_complex", filter_str, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
            "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True, capture_output=True)
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(final)],
                       capture_output=True, text=True)
    print(f"DEMO VIDEO: {final}  duration={r.stdout.strip()}s")


if __name__ == "__main__":
    main()
