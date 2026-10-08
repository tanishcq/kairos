import os
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

# Signs login tokens. Comes from .env (later a Kubernetes Secret), never from Git.
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be set to at least 32 characters (openssl rand -hex 32)")

JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(minutes=60)

# Argon2id with the library's recommended (deliberately slow) settings.
password_hash = PasswordHash.recommended()

# Checked when a login email is unknown, so a failed login takes the same time either way.
DUMMY_HASH = password_hash.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + TOKEN_LIFETIME}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id from a valid token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp"]}
        )
        return int(payload["sub"])
    except jwt.InvalidTokenError, ValueError:
        return None
