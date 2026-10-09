# frontend

The Kairos web page, served by Nginx. One container does two jobs:

1. Serves the static page (`html/`: plain HTML, CSS and JavaScript, no build step).
2. Acts as a **reverse proxy**: forwards `/api/...` to the backend services, so the browser
   only talks to one address (same origin, no CORS).

## Routing

| Browser path                          | Goes to                        |
|---------------------------------------|--------------------------------|
| `/`                                   | `html/index.html`              |
| `/health`                             | answered by Nginx: `{"status":"ok"}` |
| `/api/users`, `/api/login`, `/api/me` | `user-service:8000` (`/api` stripped)    |
| `/api/hobbies...`                     | `hobby-service:8000` (`/api` stripped)   |
| `/api/sessions...`                    | `session-service:8000` (`/api` stripped) |

The backend names are Compose DNS names (Kubernetes will provide the same names).
Nginx resolves them once at startup and refuses to start if one is missing, so the
backends must be running first (`depends_on` in `compose.yaml`).

## Run

With the full stack, from the repo root: `docker compose up -d --build`, then open
http://localhost:8088.

Compose publishes host port **8088** (container port 8080), because 8080 is often taken
by other local tools.

## Security

- Base image `nginxinc/nginx-unprivileged`: runs as a non-root user (uid 101) on port 8080.
- Headers: `Content-Security-Policy: default-src 'self'` (only our own scripts and styles,
  no inline code), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`.
  `server_tokens off` hides the Nginx version.
- User text is inserted with `textContent`, never `innerHTML`.
- The login token lives in `sessionStorage` (cleared when the tab closes) and is sent as
  `Authorization: Bearer <token>` on every API call.

## Test the config

Nginx needs the backend names to resolve, so fake them with `--add-host` (CI does the same):

```bash
docker build -t kairos-frontend:dev .
docker run --rm \
  --add-host hobby-service:127.0.0.1 \
  --add-host session-service:127.0.0.1 \
  --add-host user-service:127.0.0.1 \
  kairos-frontend:dev nginx -t
```
