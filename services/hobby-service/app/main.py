from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base, engine, get_session


class HobbyRow(Base):
    __tablename__ = "hobbies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    emoji: Mapped[str | None]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create missing tables at startup. A migration tool (Alembic) replaces this later.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="hobby-service", lifespan=lifespan)

SessionDep = Annotated[Session, Depends(get_session)]


class HobbyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    emoji: str | None = None


class Hobby(HobbyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/hobbies", status_code=status.HTTP_201_CREATED)
def create_hobby(payload: HobbyCreate, session: SessionDep) -> Hobby:
    row = HobbyRow(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return Hobby.model_validate(row)


@app.get("/hobbies")
def list_hobbies(session: SessionDep) -> list[Hobby]:
    rows = session.scalars(select(HobbyRow).order_by(HobbyRow.id))
    return [Hobby.model_validate(row) for row in rows]


@app.get("/hobbies/{hobby_id}")
def get_hobby(hobby_id: int, session: SessionDep) -> Hobby:
    row = session.get(HobbyRow, hobby_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hobby not found")
    return Hobby.model_validate(row)
