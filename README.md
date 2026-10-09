# Kairos

[![hobby-service CI](https://github.com/tanishcq/kairos/actions/workflows/hobby-service.yml/badge.svg)](https://github.com/tanishcq/kairos/actions/workflows/hobby-service.yml)
[![session-service CI](https://github.com/tanishcq/kairos/actions/workflows/session-service.yml/badge.svg)](https://github.com/tanishcq/kairos/actions/workflows/session-service.yml)
[![user-service CI](https://github.com/tanishcq/kairos/actions/workflows/user-service.yml/badge.svg)](https://github.com/tanishcq/kairos/actions/workflows/user-service.yml)
[![frontend CI](https://github.com/tanishcq/kairos/actions/workflows/frontend.yml/badge.svg)](https://github.com/tanishcq/kairos/actions/workflows/frontend.yml)

Kairos is the Greek word for "the right moment". It's a small app for people with
ADHD to park a hobby session and resume it at the right time, with solo and
shared (partner/friends) hobbies.

## Run locally

Requires Docker with Compose. From the repo root:

```bash
cp .env.example .env   # then set a real POSTGRES_PASSWORD (e.g. openssl rand -hex 16)
                       # and JWT_SECRET (openssl rand -hex 32)
docker compose up -d --build
```

- **Kairos app: http://localhost:8088** (start here)
- hobby-service: http://localhost:8000/docs
- session-service: http://localhost:8001/docs
- user-service: http://localhost:8002/docs
- PostgreSQL is only reachable inside the Compose network; data lives in the `kairos_pgdata` volume.

Stop with `docker compose down` (data is kept). `docker compose down -v` also deletes the data volume.
