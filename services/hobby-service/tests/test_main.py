from itertools import count

import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_storage(monkeypatch):
    monkeypatch.setattr(main, "_hobbies", {})
    monkeypatch.setattr(main, "_ids", count(start=1))


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
