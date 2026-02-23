from app.db.models.anime import Anime
from sqlalchemy import select

def get_anime_title_by_id(db, anime_id):
    anime = db.execute(
        select(Anime.title)
        .where(Anime.id == anime_id)
    ).scalar_one_or_none()

    return anime

def get_anime_tags(db, anime_id):
    tags = db.execute(
        select(Anime.tags)
        .where(Anime.id == anime_id)
    ).scalar_one_or_none() or []

    return tags


def get_anime_metadata_by_ids(db, anime_ids: list[int]):
    if not anime_ids:
        return {}

    rows = db.execute(
        select(Anime.id, Anime.title, Anime.tags)
        .where(Anime.id.in_(anime_ids))
    ).all()

    return {
        anime_id: {
            "title": title,
            "tags": tags or [],
        }
        for anime_id, title, tags in rows
    }
