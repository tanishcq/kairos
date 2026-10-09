from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import JWT_ALGORITHM, JWT_SECRET
from app.db import Base, get_session
from app.main import app


def auth(user_id: int) -> dict[str, str]:
    """Authorization header with a token like the ones user-service issues."""
    payload = {"sub": str(user_id), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    return {"Authorization": f"Bearer {jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)}"}


client = TestClient(app, headers=auth(1))  # every request is user 1 unless headers say otherwise
anonymous = TestClient(app)


@pytest.fixture(autouse=True)
def test_database():
    # Fresh in-memory SQLite database for every test.
    # StaticPool keeps one shared connection, otherwise each connection would get its own empty DB.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.clear()
    engine.dispose()


def park(hobby_id: int = 1, stopped: str = "Verse 1 done", step: str = "Play the chorus slowly"):
    response = client.post(
        "/sessions",
        json={"hobby_id": hobby_id, "where_i_stopped": stopped, "next_tiny_step": step},
    )
    assert response.status_code == 201
    return response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_park_session():
    session = park()
    assert session["id"] == 1
    assert session["hobby_id"] == 1
    assert session["where_i_stopped"] == "Verse 1 done"
    assert session["next_tiny_step"] == "Play the chorus slowly"
    assert session["parked_at"] is not None
    assert session["resumed_at"] is None

    response = client.get("/sessions/1")
    assert response.status_code == 200
    assert response.json() == session


def test_park_session_rejects_empty_note():
    response = client.post(
        "/sessions", json={"hobby_id": 1, "where_i_stopped": "", "next_tiny_step": "Tune up"}
    )
    assert response.status_code == 422


def test_get_missing_session_returns_404():
    response = client.get("/sessions/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_resume_session():
    park()
    response = client.post("/sessions/1/resume")
    assert response.status_code == 200
    assert response.json()["resumed_at"] is not None


def test_resume_twice_returns_409():
    park()
    client.post("/sessions/1/resume")
    response = client.post("/sessions/1/resume")
    assert response.status_code == 409
    assert response.json() == {"detail": "Session already resumed"}


def test_resume_missing_session_returns_404():
    response = client.post("/sessions/999/resume")
    assert response.status_code == 404


def test_list_sessions_filters():
    park(hobby_id=1, stopped="first")
    park(hobby_id=1, stopped="second")
    park(hobby_id=2, stopped="third")
    client.post("/sessions/1/resume")

    def stopped(params: dict) -> list[str]:
        return [s["where_i_stopped"] for s in client.get("/sessions", params=params).json()]

    assert stopped({}) == ["third", "second", "first"]  # newest first
    assert stopped({"hobby_id": 1}) == ["second", "first"]
    assert stopped({"parked": "true"}) == ["third", "second"]
    assert stopped({"parked": "false"}) == ["first"]
    assert stopped({"hobby_id": 1, "parked": "true"}) == ["second"]


def test_sessions_require_login():
    assert anonymous.get("/sessions").status_code == 401
    assert anonymous.post("/sessions/1/resume").status_code == 401
    response = anonymous.post(
        "/sessions", json={"hobby_id": 1, "where_i_stopped": "x", "next_tiny_step": "y"}
    )
    assert response.status_code == 401


def test_users_only_see_their_own_sessions():
    park(stopped="mine")
    other = auth(2)

    assert client.get("/sessions", headers=other).json() == []
    assert client.get("/sessions/1", headers=other).status_code == 404
    assert client.post("/sessions/1/resume", headers=other).status_code == 404
    assert client.get("/sessions/1").json()["resumed_at"] is None  # untouched by user 2
