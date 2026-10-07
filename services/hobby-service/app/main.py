from itertools import count

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="hobby-service")


class HobbyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    emoji: str | None = None


class Hobby(HobbyCreate):
    id: int


# In-memory storage: lost on restart. A database replaces this in a later phase.
_hobbies: dict[int, Hobby] = {}
_ids = count(start=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/hobbies", status_code=status.HTTP_201_CREATED)
def create_hobby(payload: HobbyCreate) -> Hobby:
    hobby = Hobby(id=next(_ids), **payload.model_dump())
    _hobbies[hobby.id] = hobby
    return hobby


@app.get("/hobbies")
def list_hobbies() -> list[Hobby]:
    return list(_hobbies.values())


@app.get("/hobbies/{hobby_id}")
def get_hobby(hobby_id: int) -> Hobby:
    hobby = _hobbies.get(hobby_id)
    if hobby is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hobby not found")
    return hobby
