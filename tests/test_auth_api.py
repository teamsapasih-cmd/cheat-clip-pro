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
    account = register(client, "first@example.test")
    assert account["user"]["email"] == "first@example.test"

    headers = {"Authorization": f"Bearer {account['access_token']}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == account["user"]["id"]

    login = client.post(
        "/api/auth/login",
        json={"email": "first@example.test", "password": "a-strong-password-123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == account["user"]["id"]


def test_project_data_is_scoped_to_authenticated_owner(client: TestClient):
    first = register(client, "first@example.test")
    second = register(client, "second@example.test")
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
    register(client, "same@example.test")
    response = client.post(
        "/api/auth/register",
        json={"email": "same@example.test", "password": "a-strong-password-123"},
    )
    assert response.status_code == 409
