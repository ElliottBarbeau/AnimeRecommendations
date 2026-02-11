from app.db.base import Base
from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.enums import Provider


class UserAnimeEntry(Base):
    __tablename__ = "user_anime_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer) #this needs to be a foreign key to the user table
    # add more