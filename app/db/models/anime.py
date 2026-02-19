from app.db.base import Base
from sqlalchemy import Integer, String, Enum, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.enums import Provider, AnimeStatus, AnimeType
from decimal import Decimal

class Anime(Base):
    __tablename__ = "anime"

    __table_args__ = (
        UniqueConstraint("provider", "provider_anime_id", name="uq_anime_provider_provider_anime_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[Provider] = mapped_column(Enum(Provider, name="provider_enum"), nullable=False)
    provider_anime_id: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    anime_type: Mapped[AnimeType | None] = mapped_column(Enum(AnimeType, name="anime_type_enum"), nullable=True)
    status: Mapped[AnimeStatus | None] = mapped_column(Enum(AnimeStatus, name="anime_status_enum"), nullable=True)
    episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
