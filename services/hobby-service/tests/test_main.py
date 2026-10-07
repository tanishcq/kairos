import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app

client = TestClient(app)


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
