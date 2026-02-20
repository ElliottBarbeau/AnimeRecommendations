from app.db.models.user_anime_entry import UserAnimeEntry
from sqlalchemy import select

def get_entries_above_score(db, user_id: int, score: float=8):
    recs = db.execute(
        select(UserAnimeEntry.anime_id)
        .where(UserAnimeEntry.user_id == user_id, UserAnimeEntry.score >= score)
    ).scalars().all()

    return recs

def get_neighbours(db, anime_ids: int, user_id: int, score: float=8):
    if not anime_ids:
        return []

    recs = db.execute(
        select(UserAnimeEntry.user_id)
        .where(
            UserAnimeEntry.anime_id.in_(anime_ids), 
            UserAnimeEntry.score >= score, 
            UserAnimeEntry.user_id != user_id
        )
        .distinct()
    ).scalars().all()

    return recs
    
