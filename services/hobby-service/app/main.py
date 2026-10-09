from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.auth import CurrentUserId
from app.db import Base, engine, get_session


class HobbyRow(Base):
    __tablename__ = "hobbies"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Owner: the user id ("sub") from the login token. Users live in user-service.
    user_id: Mapped[int] = mapped_column(index=True)
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
def create_hobby(payload: HobbyCreate, user_id: CurrentUserId, session: SessionDep) -> Hobby:
    row = HobbyRow(**payload.model_dump(), user_id=user_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return Hobby.model_validate(row)


@app.get("/hobbies")
def list_hobbies(user_id: CurrentUserId, session: SessionDep) -> list[Hobby]:
    query = select(HobbyRow).where(HobbyRow.user_id == user_id).order_by(HobbyRow.id)
    rows = session.scalars(query)
    return [Hobby.model_validate(row) for row in rows]


@app.get("/hobbies/{hobby_id}")
def get_hobby(hobby_id: int, user_id: CurrentUserId, session: SessionDep) -> Hobby:
    row = session.get(HobbyRow, hobby_id)
    # Someone else's hobby gets the same 404 as a missing one, so its existence isn't revealed.
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hobby not found")
    return Hobby.model_validate(row)
