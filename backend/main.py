"""EgoData Ingest API — FastAPI backend for the Data Hat phone app.

Endpoints:
  POST /ingest/upload-url   — get a presigned S3/R2 upload URL
  POST /ingest/confirm      — worker confirms upload; queues pipeline
  POST /ingest/direct       — direct multipart upload (MVP: < 100MB files)
  GET  /health              — liveness
"""
import hashlib
import hmac
import os
import time
import uuid
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="EgoData Ingest", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

# ── config (env vars or defaults) ──────────────────────────────────
UPLOAD_DIR = Path(os.getenv("EGODATA_UPLOAD_DIR", "uploads"))
RAW_BUCKET = os.getenv("EGODATA_RAW_BUCKET", "egodata-raw")
S3_ENDPOINT = os.getenv("EGODATA_S3_ENDPOINT", None)  # set for R2
S3_REGION = os.getenv("EGODATA_S3_REGION", "auto")
API_KEY = os.getenv("EGODATA_API_KEY", "")  # simple shared-secret auth
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT, region_name=S3_REGION,
                  config=BotoConfig(signature_version="s3v4"))


def _verify_key(header: str | None):
    if API_KEY and (not header or not hmac.compare_digest(
            header.removeprefix("Bearer ").strip(), API_KEY)):
        raise HTTPException(401, "invalid or missing API key")


# ── models ─────────────────────────────────────────────────────────
class UploadUrlRequest(BaseModel):
    worker_id: str
    job_type: str
    home_id: str | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    key: str
    expires_in: int = 3600


class ConfirmRequest(BaseModel):
    key: str
    worker_id: str
    duration_s: float
    hand_coverage_est: float | None = None
    task_label_count: int = 0


class ConfirmResponse(BaseModel):
    episode_id: str
    status: str  # "queued"


# ── endpoints ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "ts": time.time()}


@app.post("/ingest/upload-url", response_model=UploadUrlResponse)
def upload_url(body: UploadUrlRequest,
               authorization: str | None = Header(default=None)):
    _verify_key(authorization)
    ts = int(time.time())
    key = f"raw/{body.worker_id}/{ts}-{uuid.uuid4().hex[:8]}.mp4"
    url = s3.generate_presigned_url(
        "put_object", Params={"Bucket": RAW_BUCKET, "Key": key,
                               "ContentType": "video/mp4"},
        ExpiresIn=3600, HttpMethod="PUT")
    return UploadUrlResponse(upload_url=url, key=key)


@app.post("/ingest/direct")
async def direct_upload(file: UploadFile = File(...),
                        worker_id: str = "",
                        job_type: str = "",
                        authorization: str | None = Header(default=None)):
    """Direct multipart upload for MVP when S3 presigned is overkill."""
    _verify_key(authorization)
    ts = int(time.time())
    fname = f"{worker_id or 'anon'}/{ts}-{uuid.uuid4().hex[:8]}.mp4"
    dest = UPLOAD_DIR / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = await file.read()
    dest.write_bytes(data)
    return {"key": str(dest), "size": len(data),
            "status": "stored"}


@app.post("/ingest/confirm", response_model=ConfirmResponse)
def confirm(body: ConfirmRequest,
            authorization: str | None = Header(default=None)):
    _verify_key(authorization)
    episode_id = f"ep-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    # In production: enqueue a pipeline job (SQS / Redis / BullMQ).
    # For MVP: log to a manifest so a cron/poller picks it up.
    manifest = UPLOAD_DIR / "manifest.jsonl"
    import json
    with open(manifest, "a") as f:
        f.write(json.dumps({
            "episode_id": episode_id, "key": body.key,
            "worker_id": body.worker_id,
            "duration_s": body.duration_s,
            "hand_coverage_est": body.hand_coverage_est,
            "status": "queued", "created_at": time.time(),
        }) + "\n")
    return ConfirmResponse(episode_id=episode_id, status="queued")


# ── entrypoint ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
