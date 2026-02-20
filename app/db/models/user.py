from app.db.base import Base
from sqlalchemy import Integer, String, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.enums import Provider
import uuid

class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("provider", "provider_username", name="uq_provider_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    provider: Mapped[Provider] = mapped_column(Enum(Provider, name="provider_enum"), nullable=False)
    provider_username: Mapped[str] = mapped_column(String, nullable=False)
    provider_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stats: Mapped["UserStats"] = relationship(back_populates="user", uselist=False)

    @property
    def mean_score(self) -> float:
        if self.stats is None:
            return 0.0
        return self.stats.mean_score

    @property
    def stddev_score(self) -> float:
        if self.stats is None:
            return 0.0
        return self.stats.stddev_score

    @property
    def rating_count(self) -> int:
        if self.stats is None:
            return 0
        return self.stats.rating_count
