# EgoData — egocentric training data for home robots

**Monorepo:** capture app → ingest API → enrichment pipeline → dataset export.

A phone app + backend that turns everyday household work into structured,
rights-clean training episodes for embodied-AI and humanoid-robot labs.

**Visual-only pipeline — no audio, no narration, no transcription.**
Workers tap task labels on the phone while working. The camera captures hands.
The enrichment pipeline tracks 21 keypoints × 2 hands at 30fps, scores every
episode on hand visibility and task-label coverage, and exports in LeRobot format.

```
   Data Hat app  ──►  ingest API  ──►  enrichment pipeline  ──►  LeRobot dataset
   (Flutter)          (FastAPI)         (Python/MediaPipe)        (Parquet+mp4)

   📹 video only · 🔖 chip-tap task labels · 🤖 hand tracking · ✅ QA gate
```

---

## The pieces

| directory | what | status |
|---|---|---|
| [`app/`](app/) | Flutter phone app — USB-C camera, hand tracking, upload | scaffold complete, needs Flutter SDK to compile APK |
| [`backend/`](backend/) | FastAPI ingest API + tests (6/6 pass) | runnable |
| [`prototype/`](prototype/) | Python enrichment pipeline (hand tracking, narration, QA, export) | runnable + tested |
| [`desktop-companion/`](desktop-companion/) | Mac desktop capture app using the same pipeline | runnable (needs camera permission) |
| [`infra/`](infra/) | Docker Compose (API + pipeline worker) + deployment config | ready |
| `OUTLINE.md` | Business & technical outline (workforce, channels, economics) | draft |
| `EQUIPMENT.md` | Hardware BOM, hat-rig assembly, phone app spec | draft |

---

## Quick start

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000/health
# → http://localhost:8000/docs (OpenAPI)
```

### Enrichment pipeline (prototype)

```bash
cd prototype
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install mediapipe opencv-python-headless numpy pandas pyarrow faster-whisper
mkdir -p models && curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
python test_pipeline.py
```

### Desktop companion

```bash
cd desktop-companion
python record.py --camera 0 --max-seconds 10
```

### Full stack (Docker)

```bash
cd infra
docker compose up
```

---

## Architecture

```
                         ┌──────────────────┐
                         │  Data Hat app     │
                         │  (Flutter/Android)│
                         │  ┌──────────────┐ │
                         │  │ USB-C camera │ │
                         │  │ MediaPipe     │ │
                         │  │ local record  │ │
                         │  └──────┬───────┘ │
                         └─────────┼─────────┘
                                   │ presigned URL upload
                                   ▼
                         ┌──────────────────┐
                         │  Ingest API      │
                         │  (FastAPI)       │
                         │  ┌──────────────┐│
                         │  │ /upload-url  ││
                         │  │ /direct      ││
                         │  │ /confirm     ││
                         │  └──────┬───────┘│
                         └─────────┼─────────┘
                                   │ manifest.jsonl
                                   ▼
                         ┌──────────────────┐
                         │  Pipeline worker │
                         │  ┌──────────────┐│
                         │  │ hand tracking││
                         │  │ narration    ││
                         │  │ task labels  ││
                         │  │ QA gate      ││
                         │  │ LeRobot exp  ││
                         │  └──────────────┘│
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  Dataset store   │
                         │  (S3/R2)         │
                         │  ┌──────────────┐│
                         │  │ videos/      ││
                         │  │ data/        ││
                         │  │ meta/        ││
                         │  └──────────────┘│
                         └──────────────────┘
```

---

## What's real vs. scaffold

- **Runnable and tested:** backend API (6/6 tests), enrichment pipeline (end-to-end verified with real hand detections), desktop companion.
- **Complete scaffold, needs SDK to compile:** Flutter app (all screens, camera/USB, upload, session state — `pubspec.yaml` and all Dart files ready; `flutter build apk --release` once Flutter SDK 3.2+ is installed).
- **Design docs:** business outline (`OUTLINE.md`), equipment spec (`EQUIPMENT.md`), demo video (`prototype/assets/demo/egodata_demo.mp4`).
