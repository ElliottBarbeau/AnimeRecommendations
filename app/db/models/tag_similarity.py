from app.db.base import Base
from sqlalchemy import String, Integer, Float, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column


class TagSimilarity(Base):
    __tablename__ = "tag_similarity"

    __table_args__ = (
        CheckConstraint("source_tag <> related_tag", name="ck_tag_similarity_no_self"),
        Index("ix_tag_similarity_related_tag", "related_tag"),
    )

    source_tag: Mapped[str] = mapped_column(String, primary_key=True)
    related_tag: Mapped[str] = mapped_column(String, primary_key=True)
    cooccurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    jaccard_score: Mapped[float] = mapped_column(Float, nullable=False)
