from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import DateTime, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base, engine, get_session
from app.security import (
    DUMMY_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create missing tables at startup. A migration tool (Alembic) replaces this later.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="user-service", lifespan=lifespan)

DbSession = Annotated[Session, Depends(get_session)]
BearerToken = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]

UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> User:
    row = UserRow(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from None
    db.refresh(row)
    return User.model_validate(row)


@app.post("/login")
def login(payload: LoginRequest, db: DbSession) -> Token:
    row = db.scalar(select(UserRow).where(UserRow.email == payload.email.lower()))
    password_ok = verify_password(payload.password, row.password_hash if row else DUMMY_HASH)
    if row is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers=UNAUTHORIZED,
        )
    return Token(access_token=create_access_token(row.id))


@app.get("/me")
def me(credentials: BearerToken, db: DbSession) -> User:
    user_id = decode_access_token(credentials.credentials)
    row = db.get(UserRow, user_id) if user_id is not None else None
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers=UNAUTHORIZED,
        )
    return User.model_validate(row)
