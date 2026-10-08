from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base, engine, get_session


def utcnow() -> datetime:
    return datetime.now(UTC)


class HobbySessionRow(Base):
    __tablename__ = "hobby_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ID from hobby-service. Not a foreign key: that table belongs to another service.
    hobby_id: Mapped[int] = mapped_column(index=True)
    where_i_stopped: Mapped[str] = mapped_column(String(500))
    next_tiny_step: Mapped[str] = mapped_column(String(500))
    parked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create missing tables at startup. A migration tool (Alembic) replaces this later.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="session-service", lifespan=lifespan)

# "Session" is SQLAlchemy's database session; "HobbySession" is a parked hobby session.
DbSession = Annotated[Session, Depends(get_session)]


class HobbySessionCreate(BaseModel):
    hobby_id: int = Field(gt=0)
    where_i_stopped: str = Field(min_length=1, max_length=500)
    next_tiny_step: str = Field(min_length=1, max_length=500)


class HobbySession(HobbySessionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parked_at: datetime
    resumed_at: datetime | None


def get_row_or_404(db: Session, session_id: int) -> HobbySessionRow:
    row = db.get(HobbySessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return row


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def park_session(payload: HobbySessionCreate, db: DbSession) -> HobbySession:
    row = HobbySessionRow(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return HobbySession.model_validate(row)


@app.get("/sessions")
def list_sessions(
    db: DbSession, hobby_id: int | None = None, parked: bool | None = None
) -> list[HobbySession]:
    query = select(HobbySessionRow).order_by(HobbySessionRow.id.desc())
    if hobby_id is not None:
        query = query.where(HobbySessionRow.hobby_id == hobby_id)
    if parked is True:
        query = query.where(HobbySessionRow.resumed_at.is_(None))
    elif parked is False:
        query = query.where(HobbySessionRow.resumed_at.is_not(None))
    return [HobbySession.model_validate(row) for row in db.scalars(query)]


@app.get("/sessions/{session_id}")
def get_hobby_session(session_id: int, db: DbSession) -> HobbySession:
    return HobbySession.model_validate(get_row_or_404(db, session_id))


@app.post("/sessions/{session_id}/resume")
def resume_session(session_id: int, db: DbSession) -> HobbySession:
    row = get_row_or_404(db, session_id)
    if row.resumed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already resumed")
    row.resumed_at = utcnow()
    db.commit()
    db.refresh(row)
    return HobbySession.model_validate(row)
