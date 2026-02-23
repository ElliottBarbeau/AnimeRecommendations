from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.db.enums import Provider, AnimeStatus, AnimeType

class AnimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    provider: Provider
    provider_anime_id: int
    provider_rating: Decimal | None = None
    anime_type: AnimeType | None = None
    status: AnimeStatus | None = None
    episode_count: int | None = None
    start_year: int | None = None
    tags: list[str] = Field(default_factory=list)

class AnimeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    provider: Provider
    provider_anime_id: int
    provider_rating: Decimal | None = None
    anime_type: AnimeType | None = None
    status: AnimeStatus | None = None
    episode_count: int | None = None
    start_year: int | None = None
    tags: list[str] = Field(default_factory=list)
