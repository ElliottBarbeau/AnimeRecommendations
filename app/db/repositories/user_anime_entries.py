from app.db.models.user_anime_entry import UserAnimeEntry
from sqlalchemy import select

def get_entries_above_score(db, user_id: int, score: float=8):
    recs = db.execute(
        select(UserAnimeEntry.anime_id)
        .where(UserAnimeEntry.user_id == user_id, UserAnimeEntry.score >= score)
    ).scalars().all()

    return recs
