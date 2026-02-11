from app.db.base import Base
from sqlalchemy import Integer, String, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.db.enums import Provider, Status, AnimeType
from decimal import Decimal

class Anime(Base):
    __tablename__ = "anime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[Provider] = mapped_column(Enum(Provider, name="provider_enum"), nullable=False, unique=True)
    provider_anime_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    provider_rating: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    anime_type: Mapped[AnimeType] = mapped_column(Enum(AnimeType, name="anime_type_enum"), nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status, name="status_enum"), nullable=False)
    episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
