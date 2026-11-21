from collections.abc import Iterator
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database.dependencies import get_db_session
from backend.database.models import Base, MediaAsset
from backend.routers.auth import router as auth_router
from backend.routers.projects import router as projects_router
from backend.routers.analysis_jobs import router as analysis_jobs_router

class FakeQueue:
    def __init__(self): self.jobs = {}
    def enqueue(self, job_type, payload):
        self.jobs["job-test-1"] = {"job_type": job_type, "payload": payload}
        return type("Receipt", (), {"job_id": "job-test-1", "status": "queued"})()
    def get_progress(self, job_id): return {"status": "processing", "progress": "42", "detail": "Transcribing"}
class FakeStorage: pass

@pytest.fixture()
def client(monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-that-is-at-least-thirty-two-characters")
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    def override_db():
        db: Session = factory()
        try: yield db
        finally: db.close()
    app = FastAPI()
    app.include_router(auth_router); app.include_router(projects_router); app.include_router(analysis_jobs_router)
    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as c: yield c
    engine.dispose()

def register(c, email):
    response = c.post("/api/auth/register", json={"email": email, "password": "a-strong-password-123"})
    assert response.status_code == 201, response.text
    return response.json()

def test_analysis_job_is_owner_scoped_and_tracks_queue(monkeypatch, client):
    import backend.routers.analysis_jobs as jobs
    queue = FakeQueue()
    monkeypatch.setattr(jobs, "build_job_queue", lambda: queue)
    monkeypatch.setattr(jobs, "build_object_storage", lambda: FakeStorage())
    owner = register(client, "analysis-owner@example.com"); other = register(client, "analysis-other@example.com")
    headers = {"Authorization": f"Bearer {owner['access_token']}"}; other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    project = client.post("/api/projects", headers=headers, json={"name": "Project"}).json()
    db_gen = client.app.dependency_overrides[get_db_session](); db = next(db_gen)
    asset = MediaAsset(project_id=project["id"], owner_id=owner["user"]["id"], original_filename="source.mp4",
        storage_key="users/owner/source.mp4", source_type="upload", content_type="video/mp4", size_bytes=1024, status="uploaded")
    db.add(asset); db.commit(); asset_id = asset.id
    try: next(db_gen)
    except StopIteration: pass
    created = client.post("/api/analyses", headers=headers, json={"media_asset_id": asset_id, "duration": "30s"})
    assert created.status_code == 202, created.text
    assert created.json()["job_id"] == "job-test-1"
    assert queue.jobs["job-test-1"]["job_type"] == "analysis.run"
    status_response = client.get(f"/api/analyses/{created.json()['analysis_id']}", headers=headers)
    assert status_response.status_code == 200 and status_response.json()["progress"] == 42
    assert status_response.json()["detail"] == "Transcribing"
    assert client.get(f"/api/analyses/{created.json()['analysis_id']}", headers=other_headers).status_code == 404

def test_analysis_job_requires_uploaded_owned_media(client):
    owner = register(client, "analysis-no-media@example.com")
    response = client.post("/api/analyses", headers={"Authorization": f"Bearer {owner['access_token']}"}, json={"media_asset_id": "not-found"})
    assert response.status_code == 404
