"""Transcribe worker narration with faster-whisper -> time-aligned segments.

The worker narrates what they are doing while working; this produces the
language half of the vision-language-action training signal.
Output: JSON list of {start, end, text} segments.
"""
import argparse
import json
from pathlib import Path


def transcribe(audio_path: Path, model_size: str = "base") -> list[dict]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), vad_filter=True)
    out = [{"start": round(s.start, 2), "end": round(s.end, 2),
            "text": s.text.strip()} for s in segments]
    print(f"language={info.language} p={info.language_probability:.2f} "
          f"segments={len(out)}")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("audio", type=Path)
    p.add_argument("--model", default="base")
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    segs = transcribe(a.audio, a.model)
    out = a.out or Path("data/processed") / (a.audio.stem + "_transcript.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(segs, indent=2))
    print(f"wrote {out}")
