from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.db.enums import Provider

class UserCreate(BaseModel):
    provider: Provider
    provider_username: str
    provider_user_id: int | None = None

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    provider: Provider
    provider_username: str
    provider_user_id: int | None = None
    mean_score: float
    stddev_score: float
    rating_count: int

class UserImportMALRequest(BaseModel):
    mal_list_url: str

class UserImportMALResponse(BaseModel):
    provider: Provider
    provider_username: str
    provider_user_id: int
    pages_fetched: int
    items_seen: int
    users_created: int
    users_updated: int
    anime_created: int
    anime_updated: int
    entries_created: int
    entries_updated: int
    mean_score: float
    stddev_score: float
    rating_count: int
