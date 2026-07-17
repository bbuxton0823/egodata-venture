"""Tests for EgoData ingest API."""
import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from main import app, UPLOAD_DIR, API_KEY

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_direct_upload(tmp_path, monkeypatch):
    monkeypatch.setattr("main.UPLOAD_DIR", tmp_path)
    data = b"fake mp4 data"
    r = client.post("/ingest/direct",
                    files={"file": ("test.mp4", io.BytesIO(data), "video/mp4")},
                    data={"worker_id": "w01", "job_type": "kitchen_clean"})
    assert r.status_code == 200
    assert r.json()["status"] == "stored"
    assert r.json()["size"] == len(data)


def test_upload_url(monkeypatch):
    monkeypatch.setattr("main.s3.generate_presigned_url",
                        lambda *a, **kw: "https://fake.s3/presigned")
    r = client.post("/ingest/upload-url",
                    json={"worker_id": "w01", "job_type": "kitchen_clean"})
    assert r.status_code == 200
    body = r.json()
    assert "upload_url" in body
    assert body["key"].startswith("raw/w01/")


def test_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr("main.UPLOAD_DIR", tmp_path)
    r = client.post("/ingest/confirm",
                    json={"key": "raw/w01/abc.mp4", "worker_id": "w01",
                          "duration_s": 42.0, "hand_coverage_est": 0.85})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert body["episode_id"].startswith("ep-")
    manifest = tmp_path / "manifest.jsonl"
    assert manifest.exists()
    entry = json.loads(manifest.read_text().strip())
    assert entry["worker_id"] == "w01"


def test_auth_rejected(monkeypatch):
    monkeypatch.setattr("main.API_KEY", "secret-x")
    r = client.post("/ingest/confirm",
                    json={"key": "x", "worker_id": "w", "duration_s": 1})
    assert r.status_code == 401


def test_auth_accepted(monkeypatch, tmp_path):
    monkeypatch.setattr("main.API_KEY", "secret-x")
    monkeypatch.setattr("main.UPLOAD_DIR", tmp_path)
    r = client.post("/ingest/confirm",
                    json={"key": "x", "worker_id": "w", "duration_s": 1},
                    headers={"Authorization": "Bearer secret-x"})
    assert r.status_code == 200
