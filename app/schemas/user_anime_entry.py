from pydantic import BaseModel, ConfigDict
from app.db.enums import EntryStatus, Provider

class UserAnimeEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    provider: Provider
    provider_username: str
    anime_id: int
    status: EntryStatus | None = None
    score: int | None = None
    progress: int | None = None

class UserAnimeEntryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    anime_id: int
    status: EntryStatus | None = None
    score: int | None = None
    progress: int | None = None
