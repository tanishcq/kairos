from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import UserRow, app
from app.security import JWT_ALGORITHM, JWT_SECRET

client = TestClient(app)

EMAIL = "tan@example.com"
PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def session_factory():
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
    yield session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def register(email: str = EMAIL, password: str = PASSWORD):
    return client.post("/users", json={"email": email, "password": password})


def login(email: str = EMAIL, password: str = PASSWORD):
    return client.post("/login", json={"email": email, "password": password})


def make_token(sub: str, expires_in: timedelta, secret: str = JWT_SECRET, alg: str = JWT_ALGORITHM):
    payload = {"sub": sub, "exp": datetime.now(UTC) + expires_in}
    return jwt.encode(payload, secret, algorithm=alg)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register():
    response = register(email="Tan@Example.com")
    assert response.status_code == 201
    user = response.json()
    assert set(user) == {"id", "email", "created_at"}  # never the password or its hash
    assert user["email"] == "tan@example.com"


def test_password_is_stored_hashed(session_factory):
    register()
    with session_factory() as db:
        row = db.scalar(select(UserRow))
    assert row.password_hash.startswith("$argon2id$")
    assert PASSWORD not in row.password_hash


def test_register_duplicate_email_returns_409():
    register()
    response = register(email="TAN@example.com")
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


@pytest.mark.parametrize(
    ("email", "password"), [("not-an-email", PASSWORD), (EMAIL, "short")], ids=["email", "password"]
)
def test_register_rejects_invalid_input(email, password):
    assert register(email, password).status_code == 422


def test_login_and_me():
    register()
    response = login()
    assert response.status_code == 200
    token = response.json()
    assert token["token_type"] == "bearer"

    response = client.get("/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "wrong password"), ("nobody@example.com", PASSWORD)],
    ids=["wrong-password", "unknown-email"],
)
def test_login_failures_look_the_same(email, password):
    register()
    response = login(email, password)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_me_without_token_returns_401():
    assert client.get("/me").status_code == 401


BAD_TOKENS = {
    "garbage": "not-a-jwt",
    "expired": make_token("1", timedelta(minutes=-1)),
    "wrong-key": make_token("1", timedelta(minutes=5), secret="some-other-secret-" * 2),
    "alg-none": make_token("1", timedelta(minutes=5), secret=None, alg="none"),
    "unknown-user": make_token("999", timedelta(minutes=5)),
}


@pytest.mark.parametrize("token", BAD_TOKENS.values(), ids=BAD_TOKENS.keys())
def test_me_rejects_bad_tokens(token):
    register()
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
