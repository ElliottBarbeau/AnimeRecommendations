from app.db.models.anime import Anime
from sqlalchemy import select

def get_anime_title_by_id(db, anime_id):
    anime = db.execute(
        select(Anime.title)
        .where(Anime.id == anime_id)
    ).scalar_one_or_none()

    return anime