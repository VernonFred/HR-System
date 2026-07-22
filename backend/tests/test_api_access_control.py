import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import auth
from app.api import legacy_auth
from app.db import get_session
from app.main import app
from app.models import User
from app.security import encode_jwt, hash_password


def _fail_if_endpoint_dependency_runs():
    raise RuntimeError("protected endpoint dependencies must not run anonymously")


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_session] = _fail_if_endpoint_dependency_runs
    monkeypatch.setattr(legacy_auth, "get_engine", _fail_if_endpoint_dependency_runs)
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("GET", "/api/candidates", None),
        ("GET", "/api/assessments/submissions", None),
        ("POST", "/api/assessments", {}),
        ("DELETE", "/api/assessments/1", None),
        ("GET", "/v2/candidates", None),
        ("GET", "/questionnaires", None),
        ("GET", "/analytics/summary", None),
        ("GET", "/spec/candidates", None),
        ("POST", "/auth/register", {"username": "attacker", "password": "password"}),
    ],
)
def test_management_routes_reject_anonymous_requests(client, method, path, json_body):
    response = client.request(method, path, json=json_body)

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_public_routes_remain_outside_management_authentication(client):
    assert client.get("/health").status_code == 200
    assert client.post("/auth/login", json={}).status_code == 422
    assert client.post("/auth/refresh", json={}).status_code == 422

    public_response = client.get("/api/public/assessment/UNKNOWN")
    assert public_response.status_code != 401


def _build_protected_test_app() -> TestClient:
    protected_app = FastAPI()

    @protected_app.get("/protected")
    def protected(user_id: int = Depends(auth.get_current_user)):
        return {"user_id": user_id}

    return TestClient(protected_app)


def test_x_user_id_header_cannot_bypass_authentication(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "a" * 64)

    response = _build_protected_test_app().get(
        "/protected", headers={"X-User-Id": "1"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_refresh_token_cannot_access_management_routes(monkeypatch):
    secret = "b" * 64
    monkeypatch.setenv("JWT_SECRET", secret)
    token = encode_jwt({"sub": 1, "type": "refresh"}, secret)

    response = _build_protected_test_app().get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token type"


def test_legacy_jwt_secret_key_name_remains_compatible(monkeypatch):
    secret = "c" * 64
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    token = encode_jwt({"sub": 7, "type": "access"}, secret)

    response = _build_protected_test_app().get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": 7}


def test_non_admin_cannot_register_an_admin_account(monkeypatch):
    secret = "d" * 64
    monkeypatch.setenv("JWT_SECRET", secret)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            username="regular-user",
            password_hash=hash_password("password"),
            role="user",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    monkeypatch.setattr(auth, "get_engine", lambda: engine)
    monkeypatch.setattr(legacy_auth, "get_engine", lambda: engine)
    token = encode_jwt({"sub": user_id, "type": "access"}, secret)

    response = TestClient(app).post(
        "/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "attacker-admin", "password": "password", "role": "admin"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required"
