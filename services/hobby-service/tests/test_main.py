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


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_hobby():
    response = client.post("/hobbies", json={"name": "guitar", "emoji": "🎸"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "guitar", "emoji": "🎸"}

    response = client.get("/hobbies/1")
    assert response.status_code == 200
    assert response.json()["name"] == "guitar"


def test_list_hobbies():
    client.post("/hobbies", json={"name": "guitar"})
    client.post("/hobbies", json={"name": "painting", "emoji": "🎨"})

    response = client.get("/hobbies")
    assert response.status_code == 200
    assert [h["name"] for h in response.json()] == ["guitar", "painting"]


def test_get_missing_hobby_returns_404():
    response = client.get("/hobbies/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Hobby not found"}


def test_hobbies_require_login():
    assert anonymous.get("/hobbies").status_code == 401
    assert anonymous.post("/hobbies", json={"name": "guitar"}).status_code == 401
    bad = anonymous.get("/hobbies", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


def test_users_only_see_their_own_hobbies():
    client.post("/hobbies", json={"name": "guitar"})
    client.post("/hobbies", json={"name": "painting"}, headers=auth(2))

    assert [h["name"] for h in client.get("/hobbies").json()] == ["guitar"]
    assert [h["name"] for h in client.get("/hobbies", headers=auth(2)).json()] == ["painting"]
    assert client.get("/hobbies/1", headers=auth(2)).status_code == 404
