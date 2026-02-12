from uuid import UUID
from pydantic import BaseModel
from app.db.enums import Provider

class UserCreate(BaseModel):
    provider: Provider
    provider_username: str
    provider_user_id: int | None = None

class UserRead(BaseModel):
    id: int
    public_id: UUID
    provider: Provider
    provider_username: str
    provider_user_id: int | None = None
