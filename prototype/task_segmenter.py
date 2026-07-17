"""Task segmentation + labeling: align narration transcript to a task taxonomy.

Maps each narration segment to a task label via keyword rules (prototype-grade;
production swaps in a model fine-tuned on Ego4D/EPIC-KITCHENS). Emits
time-coded task episodes.
"""
import argparse
import json
import re
from pathlib import Path

TAXONOMY = {
    "pick_up(plate)": [r"\bpick(?:ing)? up (?:the )?(?:plate|dish)", r"\bgrab(?:bing)? (?:the )?(?:plate|dish)"],
    "rinse(plate)": [r"\brins(?:e|ing)", r"\bunder (?:the )?(?:tap|faucet|water)"],
    "scrub(plate)": [r"\bscrub(?:bing)?", r"\bsponge\b", r"\bsoap"],
    "wipe(plate)": [r"\bwip(?:e|ing) (?:the )?(?:plate|dish)", r"\bdry(?:ing)? (?:the )?(?:plate|dish)"],
    "wipe(surface)": [r"\bwip(?:e|ing) (?:the )?(?:counter|surface|table)", r"\bclean(?:ing)? (?:the )?counter"],
    "place(plate,rack)": [r"\b(?:place|put)(?:ting)? (?:it |the plate )?in (?:the )?(?:rack|drying rack)", r"\bput(?:ting)? (?:the )?(?:plate|dish) (?:away|in the rack)"],
    "fold(cloth)": [r"\bfold(?:ing)? (?:the )?(?:towel|cloth|laundry)"],
    "load(dishwasher)": [r"\bload(?:ing)? (?:the )?dishwasher"],
    "pour(liquid)": [r"\bpour(?:ing)?"],
    "sweep(floor)": [r"\bsweep(?:ing)?", r"\bbroom"],
    "idle/other": [r".*"],
}


def label_text(text: str) -> str:
    t = text.lower()
    for label, patterns in TAXONOMY.items():
        for pat in patterns:
            if re.search(pat, t):
                return label
    return "idle/other"


def segment_tasks(transcript: list[dict]) -> list[dict]:
    episodes = []
    for seg in transcript:
        episodes.append({
            "start": seg["start"], "end": seg["end"],
            "task": label_text(seg["text"]), "narration": seg["text"],
        })
    # merge consecutive identical labels
    merged = []
    for ep in episodes:
        if merged and merged[-1]["task"] == ep["task"]:
            merged[-1]["end"] = ep["end"]
            merged[-1]["narration"] += " " + ep["narration"]
        else:
            merged.append(dict(ep))
    return merged


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("transcript", type=Path, help="transcript JSON from narration_transcribe.py")
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    transcript = json.loads(a.transcript.read_text())
    tasks = segment_tasks(transcript)
    out = a.out or Path("data/processed") / (a.transcript.stem.replace("_transcript", "") + "_tasks.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(tasks, indent=2))
    print(json.dumps(tasks, indent=2))
    print(f"wrote {out}")
