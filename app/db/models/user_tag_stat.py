from app.db.base import Base
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class UserTagStat(Base):
    __tablename__ = "user_tag_stats"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tag: Mapped[str] = mapped_column(String, primary_key=True)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
