from app.db.models.user_anime_entry import UserAnimeEntry
from sqlalchemy import select

def get_entries_above_z_score(db, user_id: int, z_score_threshold: float = 1.0):
    recs = db.execute(
        select(UserAnimeEntry.anime_id)
        .where(
            UserAnimeEntry.user_id == user_id,
            UserAnimeEntry.z_score.is_not(None),
            UserAnimeEntry.z_score >= z_score_threshold,
        ),
    ).scalars().all()

    return recs

def get_neighbours(db, anime_ids: list[int], user_id: int, z_score_threshold: float = 1.0):
    if not anime_ids:
        return []

    recs = db.execute(
        select(UserAnimeEntry.user_id)
        .where(
            UserAnimeEntry.anime_id.in_(anime_ids), 
            UserAnimeEntry.z_score.is_not(None),
            UserAnimeEntry.z_score >= z_score_threshold, 
            UserAnimeEntry.user_id != user_id,
        )
        .distinct()
    ).scalars().all()

    return recs

def get_candidate_shows(db, neighbours: list, user_id: int, z_score_threshold: float = 1.0):
    if not neighbours:
        return []
    
    seen_subquery = (
        select(UserAnimeEntry.anime_id)
        .where(UserAnimeEntry.user_id == user_id)
    )
    
    recs = db.execute(
        select(UserAnimeEntry.anime_id)
        .where(
            UserAnimeEntry.user_id.in_(neighbours),
            UserAnimeEntry.z_score.is_not(None),
            UserAnimeEntry.z_score >= z_score_threshold,
            ~UserAnimeEntry.anime_id.in_(seen_subquery),
        )
    ).scalars().all()

    return recs
    
