"""Build the shareable demo video: stills + real hand tracking + VO.

All frames are rendered in OpenCV (no ffmpeg drawtext dependency); ffmpeg is
used only to encode H.264 and mux the macOS `say` narration.
Output: assets/demo/egodata_demo.mp4 (1080p30, H.264 + AAC)
"""
import subprocess
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision, BaseOptions

ROOT = Path(__file__).parent
STILLS = ROOT / "assets" / "stills"
VO = ROOT / "assets" / "vo"
OUT = ROOT / "assets" / "demo"
OUT.mkdir(parents=True, exist_ok=True)

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
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(dur)]
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
    """Yield frames with slow zoom/pan. fx(frame, t01) draws overlays."""
    n = int(dur * FPS)
    big = cv2.resize(img, (int(W * 1.15), int(H * 1.15)),
                     interpolation=cv2.INTER_AREA)
    for f in range(n):
        t01 = f / max(n - 1, 1)
        z = 1.15 - 0.15 * t01 if not zoom_in else 1.0 + 0.15 * t01
        cw, ch = int(W * z), int(H * z)
        max_x, max_y = big.shape[1] - cw, big.shape[0] - ch
        # gentle drift for life
        ox = int(max_x * (0.5 + 0.2 * np.sin(t01 * np.pi)))
        oy = int(max_y * (0.5 - 0.2 * np.cos(t01 * np.pi)))
        crop = big[oy:oy + ch, ox:ox + cw]
        frame = cv2.resize(crop, (W, H), interpolation=cv2.INTER_AREA)
        if fx:
            fx(frame, t01, z, ox, oy, big.shape)
        yield frame


def badge(frame, s, top_right=True):
    (tw, th), _ = cv2.getTextSize(s, FONT, 0.85, 2)
    x = W - tw - 60 if top_right else 40
    cv2.rectangle(frame, (x - 14, 30), (x + tw + 14, 30 + th + 24), DARK, -1)
    text(frame, s, x, 30 + th + 6, 0.85, WHITE, 2)


def detect_hands(img_path):
    opts = vision.HandLandmarkerOptions(
        base_options=BaseOptions(
            model_asset_path=str(ROOT / "models" / "hand_landmarker.task")),
        running_mode=vision.RunningMode.IMAGE, num_hands=2)
    det = vision.HandLandmarker.create_from_options(opts)
    img = cv2.imread(str(img_path))
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                      data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    res = det.detect(mp_img)
    det.close()
    return [[(p.x, p.y) for p in lm] for lm in res.hand_landmarks]


def seg_title(out, lines, dur, sub=None, vo=None, bg=DARK):
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)
    for _ in range(int(dur * FPS)):
        frame = np.full((H, W, 3), bg, np.uint8)
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

    def overlays(frame, t01, *_):
        if caption:
            text(frame, caption, 60, H - 90, 1.1, WHITE, 2)
        if badge_text:
            badge(frame, badge_text)
        # subtle bottom bar
        cv2.rectangle(frame, (0, H - 6), (int(W * t01), H), ACCENT, -1)

    for fr in ken_burns_segment(img, dur, zoom_in, overlays):
        vw.write(fr)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def seg_pov_tracked(out, img_path, dur, task_label, vo=None, zoom_in=True):
    img = load_cover(img_path)
    base_hands = detect_hands(img_path)
    if not base_hands:
        raise RuntimeError(f"no hands in {img_path}")
    p = out.with_suffix(".silent.mp4")
    vw = writer(p)

    def overlays(frame, t01, z, ox, oy, big_shape):
        bw, bh = big_shape[1], big_shape[0]
        sx, sy = W / (W * z), H / (H * z)
        # image coords in 'big' space: still covers W*1.15 x H*1.15
        scale_to_big = bw / img.shape[1]
        for hand in base_hands:
            pts = []
            for px, py in hand:
                bx, by = px * bw, py * bh
                fx, fy = (bx - ox) * sx, (by - oy) * sy
                pts.append((int(fx), int(fy)))
            for a, b in CONNECTIONS:
                cv2.line(frame, pts[a], pts[b], GREEN, 3, cv2.LINE_AA)
            for pt in pts:
                cv2.circle(frame, pt, 4, RED, -1)
        cv2.rectangle(frame, (0, 0), (W, 58), DARK, -1)
        t = t01 * dur
        text(frame, f"EGO-CAM 01   REC {t:05.1f}s   "
                    f"{len(base_hands)} hands x 21 keypoints   30 fps",
             26, 38, 0.8, WHITE, 2)
        cv2.circle(frame, (W - 120, 29), 9, (60, 60, 255), -1)
        text(frame, "REC", W - 95, 38, 0.8, (60, 60, 255), 2)
        text(frame, f"task: {task_label}", 26, H - 36, 1.2, GREEN, 2)

    for fr in ken_burns_segment(img, dur, zoom_in, overlays):
        vw.write(fr)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def seg_qa(out, dur, vo=None):
    metrics = [("hand visibility", 0.94, 0.70),
               ("narration coverage", 0.88, 0.50),
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
            cv2.rectangle(frame, (60, y + 20), (60 + bar_w, y + 62),
                          (60, 60, 60), -1)
            cv2.rectangle(frame, (60, y + 20),
                          (60 + int(bar_w * shown), y + 62), GREEN, -1)
            tx = 60 + int(bar_w * thr)
            cv2.line(frame, (tx, y + 12), (tx, y + 70), (200, 200, 200), 2)
            text(frame, f"{shown*100:4.1f}%  (min {int(thr*100)}%)",
                 60 + bar_w + 40, y + 54, 0.95, WHITE, 2)
            y += 175
        if t01 > 0.65:
            alpha = min(1.0, (t01 - 0.65) / 0.15)
            col = tuple(int(c * alpha) for c in GREEN)
            text(frame, "EPISODE ACCEPTED", 60, y + 60, 1.7, col, 4)
        vw.write(frame)
    vw.release()
    encode_audio_mux(p, vo, dur, out)
    return out


def main():
    segs = []
    plan = [
        ("01_title", lambda o: seg_title(
            o, ["First-person data", "for home robots"], 1.8,
            sub="what a capture shift looks like")),
        ("02_meet", lambda o: seg_still(
            o, STILLS / "a_front.png", 6.2,
            caption="Head-cam pointed at the hands",
            badge_text="CAPTURE SHIFT · KITCHEN CLEAN", vo=VO / "vo1.wav")),
        ("03_high", lambda o: seg_still(
            o, STILLS / "b_high.png", 5.6, caption="Real work, real homes",
            badge_text="ANGLE 2", vo=VO / "vo2.wav", zoom_in=False)),
        ("04_pov_tracked", lambda o: seg_pov_tracked(
            o, STILLS / "c_pov.png", 7.0, "wipe(plate)", vo=VO / "vo3.wav")),
        ("05_pov_labels", lambda o: seg_pov_tracked(
            o, STILLS / "f_pov_fold.png", 6.0, "fold(cloth)",
            vo=VO / "vo4.wav", zoom_in=False)),
        ("06_qa", lambda o: seg_qa(o, 6.4, vo=VO / "vo5.wav")),
        ("07_dataset", lambda o: seg_still(
            o, STILLS / "d_front_sink.png", 5.6,
            caption="Enriched episodes, exported LeRobot-ready",
            badge_text="videos/  data/  meta/", vo=VO / "vo6.wav",
            zoom_in=False)),
        ("08_end", lambda o: seg_title(
            o, ["Real homes. Real tasks. Real data."], 3.4,
            sub="egocentric capture · hand tracking · task labels · QA",
            vo=VO / "vo7.wav")),
    ]
    for name, fn in plan:
        seg_path = OUT / f"{name}.mp4"
        print("render", name)
        fn(seg_path)
        segs.append(seg_path)

    concat = OUT / "concat.txt"
    concat.write_text("".join(f"file '{s.resolve()}'\n" for s in segs))
    final = OUT / "egodata_demo.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    str(concat), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-movflags", "+faststart", str(final)],
                   check=True, capture_output=True)
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(final)],
                       capture_output=True, text=True)
    print(f"DEMO VIDEO: {final}  duration={r.stdout.strip()}s")


if __name__ == "__main__":
    main()
