# hobby-service

Kairos service for managing hobbies. FastAPI, in-memory storage for now
(data is lost on restart; PostgreSQL comes in a later phase).

## Endpoints

| Method | Path                 | Description                         |
|--------|----------------------|-------------------------------------|
| GET    | `/health`            | Health check, returns `{"status": "ok"}` |
| POST   | `/hobbies`           | Create a hobby (`name`, optional `emoji`), returns 201 |
| GET    | `/hobbies`           | List all hobbies                    |
| GET    | `/hobbies/{id}`      | Get one hobby, 404 if missing       |

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
uvicorn app.main:app --reload
```

Then open http://localhost:8000/health. Stop with Ctrl+C.

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
