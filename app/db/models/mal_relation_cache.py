from app.db.base import Base
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column


class MalRelationCache(Base):
    __tablename__ = "mal_relation_cache"

    provider_anime_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    related_prequel_sequel_mal_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
