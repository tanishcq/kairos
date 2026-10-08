# user-service

Kairos service for accounts: register, log in, and get a token that proves who you are.
FastAPI + SQLAlchemy, stored in PostgreSQL (via Docker Compose) or a local SQLite file when
run without Postgres. Passwords are hashed with Argon2id (pwdlib); tokens are JWTs (PyJWT, HS256).

## Endpoints

| Method | Path      | Description                                                         |
|--------|-----------|---------------------------------------------------------------------|
| GET    | `/health` | Health check, returns `{"status": "ok"}`                            |
| POST   | `/users`  | Register (`email`, `password` 8-128 chars), returns 201, 409 if the email is taken |
| POST   | `/login`  | `email` + `password` -> `{"access_token": ..., "token_type": "bearer"}`, 401 if wrong |
| GET    | `/me`     | Current user. Needs `Authorization: Bearer <token>`, 401 if missing, invalid or expired |

Emails are stored lowercase. Responses never include the password or its hash.
Tokens contain only `sub` (user id), `iat` and `exp` (60 minutes). A JWT is signed, not
encrypted: anyone can read it, so it holds no personal data.

Interactive API docs: http://localhost:8002/docs (via Docker Compose). Use the **Authorize**
button to paste a token and try `/me`.

## Setup

Requires Python 3.14 (tested on 3.14.4). Run from `services/user-service`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements.txt` holds runtime dependencies; `requirements-dev.txt` adds test and lint tools.

## Run

```bash
export JWT_SECRET=$(openssl rand -hex 32)
uvicorn app.main:app --reload
```

Then open http://localhost:8000/health. Stop with Ctrl+C.
Without `DATABASE_URL` set, data goes to `user-dev.db` (gitignored).

## Configuration

| Variable       | Default                   | Notes                                                  |
|----------------|---------------------------|--------------------------------------------------------|
| `DATABASE_URL` | `sqlite:///./user-dev.db` | e.g. `postgresql+psycopg://user:pass@postgres:5432/kairos` |
| `JWT_SECRET`   | none (required)           | Signs tokens. 32+ characters, e.g. `openssl rand -hex 32`. The service refuses to start without it. |

Keep `JWT_SECRET` in the root `.env` (gitignored), never in Git. Changing it logs everyone out
(existing tokens stop working); no data is lost. Tables are created at startup if missing.

## Docker

Build and run the image on its own. `/app` is read-only for the non-root user, so point
SQLite at `/tmp` (data is lost when the container is removed):

```bash
docker build -t kairos-user-service:dev .
docker run --rm -p 8002:8000 -e DATABASE_URL=sqlite:////tmp/user.db \
  -e JWT_SECRET=$(openssl rand -hex 32) kairos-user-service:dev
```

The image is multi-stage, based on `python:3.14-slim`, and runs as the non-root user `kairos` (UID 10001).
For the full stack with PostgreSQL, see the root README.

## Test

```bash
pytest -v
```

`tests/conftest.py` sets a fake `JWT_SECRET`, so tests (and CI) need no real secret.

## Lint and format

```bash
ruff check .
ruff format --check .
```

To apply formatting: `ruff format .`
