from app.db.base import Base
from sqlalchemy import Integer, Enum, Numeric, Float, ForeignKey, UniqueConstraint, ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.enums import EntryStatus
from decimal import Decimal

class UserAnimeEntry(Base):
    __tablename__ = "user_anime_entries"

    __table_args__ = (
        UniqueConstraint("user_id", "anime_id", name="uq_userid_animeid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    anime_id: Mapped[int] = mapped_column(ForeignKey("anime.id"), nullable=False)
    status: Mapped[EntryStatus] = mapped_column(Enum(EntryStatus, name="entry_status_enum"), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    z_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
