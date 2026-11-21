from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.dependencies import get_db_session
from backend.database.models import Base
from backend.routers.auth import router as auth_router
from backend.routers.projects import router as projects_router
from backend.routers.cloud_media import router as cloud_media_router


@pytest.fixture()
def client(monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-that-is-at-least-thirty-two-characters")
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
    app.include_router(cloud_media_router)
    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "a-strong-password-123", "display_name": "Test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_register_login_and_current_user(client: TestClient):
    account = register(client, "first@example.com")
    assert account["user"]["email"] == "first@example.com"

    headers = {"Authorization": f"Bearer {account['access_token']}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == account["user"]["id"]

    login = client.post(
        "/api/auth/login",
        json={"email": "first@example.com", "password": "a-strong-password-123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == account["user"]["id"]


def test_project_data_is_scoped_to_authenticated_owner(client: TestClient):
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}

    created = client.post(
        "/api/projects",
        headers=first_headers,
        json={"name": "Private project", "description": "Only owner can see this"},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    assert client.get("/api/projects", headers=first_headers).json()[0]["id"] == project_id
    assert client.get("/api/projects", headers=second_headers).json() == []
    assert client.get(f"/api/projects/{project_id}", headers=second_headers).status_code == 404
    assert client.delete(f"/api/projects/{project_id}", headers=second_headers).status_code == 404


def test_project_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/projects", json={"name": "No auth"}).status_code == 401


def test_duplicate_registration_is_rejected(client: TestClient):
    register(client, "same@example.com")
    response = client.post(
        "/api/auth/register",
        json={"email": "same@example.com", "password": "a-strong-password-123"},
    )
    assert response.status_code == 409


def test_registration_fails_safely_when_jwt_secret_is_missing(client: TestClient, monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    response = client.post(
        "/api/auth/register",
        json={"email": "secret-missing@example.com", "password": "a-strong-password-123"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]

    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-that-is-at-least-thirty-two-characters")
    retry = client.post(
        "/api/auth/register",
        json={"email": "secret-missing@example.com", "password": "a-strong-password-123"},
    )
    assert retry.status_code == 201, retry.text


class FakeObjectStorage:
    def __init__(self):
        self.expected_size = 0
        self.expected_type = ""

    def create_upload_url(self, key: str, content_type: str, expires_seconds: int = 300) -> str:
        self.expected_type = content_type
        return "https://storage.example.test/signed-upload"

    def get_metadata(self, key: str) -> dict[str, object]:
        return {"size_bytes": self.expected_size, "content_type": self.expected_type}


def test_cloud_upload_requires_owned_project_and_verifies_object(client: TestClient, monkeypatch):
    import backend.routers.cloud_media as cloud_media

    storage = FakeObjectStorage()
    monkeypatch.setattr(cloud_media, "build_object_storage", lambda: storage)

    first = register(client, "media-owner@example.com")
    second = register(client, "other-owner@example.com")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}

    project = client.post(
        "/api/projects", headers=first_headers, json={"name": "Media project"}
    ).json()

    denied = client.post(
        "/api/media/cloud/upload-intent",
        headers=second_headers,
        json={
            "project_id": project["id"],
            "filename": "clip.mp4",
            "content_type": "video/mp4",
            "size_bytes": 1024,
        },
    )
    assert denied.status_code == 404

    intent = client.post(
        "/api/media/cloud/upload-intent",
        headers=first_headers,
        json={
            "project_id": project["id"],
            "filename": "../../clip.mp4",
            "content_type": "video/mp4",
            "size_bytes": 1024,
        },
    )
    assert intent.status_code == 201, intent.text
    assert intent.json()["method"] == "PUT"
    assert intent.json()["required_headers"]["Content-Type"] == "video/mp4"
    assert intent.json()["media_asset_id"]

    storage.expected_size = 1024
    completed = client.post(
        f"/api/media/cloud/{intent.json()['media_asset_id']}/complete",
        headers=first_headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "uploaded"

    hidden = client.post(
        f"/api/media/cloud/{intent.json()['media_asset_id']}/complete",
        headers=second_headers,
    )
    assert hidden.status_code == 404


def test_cloud_upload_rejects_unsupported_content_type(client: TestClient, monkeypatch):
    import backend.routers.cloud_media as cloud_media

    monkeypatch.setattr(cloud_media, "build_object_storage", lambda: FakeObjectStorage())
    account = register(client, "media-type@example.com")
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    project = client.post(
        "/api/projects", headers=headers, json={"name": "Media project"}
    ).json()
    response = client.post(
        "/api/media/cloud/upload-intent",
        headers=headers,
        json={
            "project_id": project["id"],
            "filename": "not-video.exe",
            "content_type": "application/x-msdownload",
            "size_bytes": 1024,
        },
    )
    assert response.status_code == 415
