import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Postgres in Compose/Kubernetes, e.g. postgresql+psycopg://user:pass@postgres:5432/kairos
# Falls back to a local SQLite file so the app also runs without Postgres.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./user-dev.db")

# SQLite refuses by default to share a connection across threads; FastAPI uses a thread pool.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
