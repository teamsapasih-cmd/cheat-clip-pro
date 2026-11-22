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
    def __init__(self):
        self.jobs = {}

    def enqueue(self, job_type, payload):
        self.jobs["job-test-1"] = {"job_type": job_type, "payload": payload}
        return type("Receipt", (), {"job_id": "job-test-1", "status": "queued"})()

    def get_progress(self, job_id):
        return {"status": "processing", "progress": "42", "detail": "Transcribing"}


class FakeStorage:
    pass


@pytest.fixture()
def client(monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-that-is-at-least-thirty-two-characters")
    # Keep API tests deterministic; distributed rate-limit behavior is tested separately.
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "false")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db: Session = factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(analysis_jobs_router)
    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def register(client: TestClient, email: str):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "a-strong-password-123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_uploaded_asset(client: TestClient, owner_token: str, email: str) -> str:
    import backend.routers.analysis_jobs as jobs

    project = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Project"},
    ).json()
    user = client.get("/api/auth/me", headers={"Authorization": f"Bearer {owner_token}"}).json()
    db_generator = client.app.dependency_overrides[get_db_session]()
    db = next(db_generator)
    asset = MediaAsset(
        project_id=project["id"],
        owner_id=user["id"],
        original_filename="source.mp4",
        storage_key=f"users/{email}/source.mp4",
        source_type="upload",
        content_type="video/mp4",
        size_bytes=1024,
        status="uploaded",
    )
    db.add(asset)
    db.commit()
    asset_id = asset.id
    try:
        next(db_generator)
    except StopIteration:
        pass
    return asset_id


def test_analysis_job_is_owner_scoped_and_tracks_queue(monkeypatch, client):
    import backend.routers.analysis_jobs as jobs

    queue = FakeQueue()
    monkeypatch.setattr(jobs, "build_job_queue", lambda: queue)
    monkeypatch.setattr(jobs, "build_object_storage", lambda: FakeStorage())
    owner = register(client, "analysis-owner@example.com")
    other = register(client, "analysis-other@example.com")
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    asset_id = create_uploaded_asset(client, owner["access_token"], "analysis-owner")

    created = client.post(
        "/api/analyses",
        headers=headers,
        json={"media_asset_id": asset_id, "duration": "30s"},
    )
    assert created.status_code == 202, created.text
    assert created.json()["job_id"] == "job-test-1"
    assert queue.jobs["job-test-1"]["job_type"] == "analysis.run"
    status_response = client.get(
        f"/api/analyses/{created.json()['analysis_id']}",
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["progress"] == 42
    assert status_response.json()["detail"] == "Transcribing"
    assert client.get(
        f"/api/analyses/{created.json()['analysis_id']}",
        headers=other_headers,
    ).status_code == 404


@pytest.mark.parametrize("clip_count", [0, -1, 201, 1000000])
def test_analysis_job_rejects_out_of_range_clip_count(monkeypatch, client, clip_count):
    import backend.routers.analysis_jobs as jobs

    monkeypatch.setattr(jobs, "build_job_queue", lambda: FakeQueue())
    monkeypatch.setattr(jobs, "build_object_storage", lambda: FakeStorage())
    owner = register(client, f"analysis-invalid-{clip_count}@example.com")
    asset_id = create_uploaded_asset(client, owner["access_token"], f"analysis-invalid-{clip_count}")
    response = client.post(
        "/api/analyses",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={"media_asset_id": asset_id, "target_clip_count": clip_count},
    )
    assert response.status_code == 422


def test_analysis_job_accepts_auto_and_maximum_clip_count(monkeypatch, client):
    import backend.routers.analysis_jobs as jobs

    queue = FakeQueue()
    monkeypatch.setattr(jobs, "build_job_queue", lambda: queue)
    monkeypatch.setattr(jobs, "build_object_storage", lambda: FakeStorage())
    owner = register(client, "analysis-valid-count@example.com")
    asset_id = create_uploaded_asset(client, owner["access_token"], "analysis-valid-count")
    for value in ("auto", 200, 1):
        response = client.post(
            "/api/analyses",
            headers={"Authorization": f"Bearer {owner['access_token']}"},
            json={"media_asset_id": asset_id, "target_clip_count": value},
        )
        assert response.status_code == 202, response.text


def test_analysis_job_requires_uploaded_owned_media(client):
    owner = register(client, "analysis-no-media@example.com")
    response = client.post(
        "/api/analyses",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={"media_asset_id": "not-found"},
    )
    assert response.status_code == 404
