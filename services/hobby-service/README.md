# hobby-service

Kairos service for managing hobbies. FastAPI + SQLAlchemy, stored in PostgreSQL
(via Docker Compose) or a local SQLite file when run without Postgres.

## Endpoints

| Method | Path                 | Description                         |
|--------|----------------------|-------------------------------------|
| GET    | `/health`            | Health check, returns `{"status": "ok"}` |
| POST   | `/hobbies`           | Create a hobby (`name`, optional `emoji`), returns 201 |
| GET    | `/hobbies`           | List all hobbies                    |
| GET    | `/hobbies/{id}`      | Get one hobby, 404 if missing       |

All endpoints except `/health` need a login token from user-service:
`Authorization: Bearer <token>` (401 without it). Each user only sees their own data;
someone else's hobby returns 404, the same as a missing one.

Interactive API docs: http://localhost:8000/docs (while the service is running).

## Setup

Requires Python 3.14 (tested on 3.14.4). Run from `services/hobby-service`:

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
Without `DATABASE_URL` set, data goes to `hobby-dev.db` (gitignored).

## Configuration

| Variable       | Default                    | Example (Compose)                                      |
|----------------|----------------------------|--------------------------------------------------------|
| `DATABASE_URL` | `sqlite:///./hobby-dev.db` | `postgresql+psycopg://user:pass@postgres:5432/kairos`  |
| `JWT_SECRET`   | none (required) | Same value as user-service; verifies login tokens. 32+ characters. |

Tables are created at startup if missing.

## Docker

Build and run the image on its own. `/app` is read-only for the non-root user, so point
SQLite at `/tmp` (data is lost when the container is removed):

```bash
docker build -t kairos-hobby-service:dev .
docker run --rm -p 8000:8000 -e DATABASE_URL=sqlite:////tmp/hobby.db \
  -e JWT_SECRET=$(openssl rand -hex 32) kairos-hobby-service:dev
```

The image is multi-stage, based on `python:3.14-slim`, and runs as the non-root user `kairos` (UID 10001).
For the full stack with PostgreSQL, see the root README.

## Test

```bash
pytest -v
```

## Lint and format

```bash
ruff check .
ruff format --check .
```

To apply formatting: `ruff format .`
