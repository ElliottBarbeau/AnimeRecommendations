from pydantic import BaseModel, ConfigDict, Field
from app.db.enums import EntryStatus, Provider

class UserAnimeEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    provider: Provider
    provider_username: str
    anime_id: int
    anime_title: str
    status: EntryStatus | None = None
    score: int | None = None
    z_score: float | None = None
    progress: int | None = None
    tags: list[str] = Field(default_factory=list)

class UserAnimeEntryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    anime_id: int
    status: EntryStatus | None = None
    score: int | None = None
    progress: int | None = None
