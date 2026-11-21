from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.database.models import Base, User, Project, RenderJob, ExportedVideo
from backend.services.legacy_render_export import persist_legacy_batch_exports


class FakeStorage:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put(self, key, body, content_type):
        data = body.read()
        self.objects[key] = (data, content_type)
        return type("Stored", (), {"size_bytes": len(data), "content_type": content_type})()

    def create_download_url(self, key, expires_seconds=300):
        return f"https://storage.invalid/{key}?expires={expires_seconds}"

    def delete(self, key):
        self.deleted.append(key)
        self.objects.pop(key, None)


def test_legacy_render_exports_are_saved_with_expiry_and_idempotent(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="render-cloud@example.com")
    db.add(user)
    db.flush()
    project = Project(owner_id=user.id, name="Cloud project")
    db.add(project)
    db.commit()

    mp4 = tmp_path / "clip-01.mp4"
    mp4.write_bytes(b"test-video-bytes")
    zip_file = tmp_path / "cheat_clip_pro_batch_test_123.zip"
    zip_file.write_bytes(b"test-zip-bytes")
    batch = {
        "overall_status": "completed",
        "clips": [{
            "status": "completed",
            "output_path": str(mp4),
            "download_url": "/api/download-rendered/clip-01.mp4",
        }],
    }
    storage = FakeStorage()
    now = datetime(2026, 11, 21, tzinfo=timezone.utc)

    first = persist_legacy_batch_exports(
        db, storage, owner_id=user.id, project=project,
        batch_id="batch_test_123", batch=batch, exports_dir=tmp_path, now=now,
    )
    assert first["already_saved"] is False
    assert len(first["exports"]) == 2
    assert all(item["expires_at"] == "2026-11-28T00:00:00+00:00" for item in first["exports"])
    assert len(storage.objects) == 2

    second = persist_legacy_batch_exports(
        db, storage, owner_id=user.id, project=project,
        batch_id="batch_test_123", batch=batch, exports_dir=tmp_path, now=now,
    )
    assert second["already_saved"] is True
    assert second["render_job_id"] == first["render_job_id"]
    assert len(db.scalars(select(ExportedVideo)).all()) == 2
    assert len(db.scalars(select(RenderJob)).all()) == 1
    db.close()


def test_legacy_render_cloud_save_rejects_non_completed_batch(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="render-pending@example.com")
    db.add(user)
    db.flush()
    project = Project(owner_id=user.id, name="Pending")
    db.add(project)
    db.commit()

    try:
        persist_legacy_batch_exports(
            db, FakeStorage(), owner_id=user.id, project=project,
            batch_id="batch_pending", batch={"overall_status": "running", "clips": []},
            exports_dir=tmp_path,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass
    db.close()


def test_legacy_render_cloud_save_rejects_file_over_free_tier_limit(tmp_path: Path, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="render-large@example.com")
    db.add(user)
    db.flush()
    project = Project(owner_id=user.id, name="Large export")
    db.add(project)
    db.commit()

    mp4 = tmp_path / "large.mp4"
    mp4.write_bytes(b"0123456789")
    monkeypatch.setenv("MAX_CLOUD_UPLOAD_BYTES", "5")
    storage = FakeStorage()
    try:
        persist_legacy_batch_exports(
            db, storage, owner_id=user.id, project=project,
            batch_id="batch_large", batch={"overall_status": "completed", "clips": [{"status": "completed", "output_path": str(mp4)}]},
            exports_dir=tmp_path,
        )
        assert False, "expected ValueError for an oversized cloud export"
    except ValueError as error:
        assert "Cloud storage limit" in str(error)
    assert storage.objects == {}
    db.close()
