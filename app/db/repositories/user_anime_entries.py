from app.db.models.user_anime_entry import UserAnimeEntry
from app.db.models.user_tag_stat import UserTagStat
from app.db.models.anime import Anime
from sqlalchemy import select, func

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
        select(
            UserAnimeEntry.anime_id,
            func.sum(UserAnimeEntry.z_score).label("base_score"),
            func.count(UserAnimeEntry.user_id).label("support_count"),
        )
        .where(
            UserAnimeEntry.user_id.in_(neighbours),
            UserAnimeEntry.z_score.is_not(None),
            UserAnimeEntry.z_score >= z_score_threshold,
            ~UserAnimeEntry.anime_id.in_(seen_subquery),
        )
        .group_by(UserAnimeEntry.anime_id)
    ).all()

    return [
        {
            "anime_id": anime_id,
            "base_score": float(base_score) if base_score is not None else 0.0,
            "support_count": int(support_count),
        }
        for anime_id, base_score, support_count in recs
    ]

def get_average_rating_by_tag(db, user_id: int, tag: str):
    average_score = db.execute(
        select(UserTagStat.avg_z_score)
        .where(
            UserTagStat.user_id == user_id,
            UserTagStat.tag == tag,
        )
    ).scalar_one_or_none()

    return average_score


def get_user_tag_preferences(db, user_id: int):
    rows = db.execute(
        select(UserTagStat.tag, UserTagStat.avg_z_score, UserTagStat.z_score_count)
        .where(UserTagStat.user_id == user_id)
    ).all()

    return {
        tag: {
            "avg_z_score": (float(avg_z_score) if avg_z_score is not None else None),
            "z_score_count": z_score_count,
        }
        for tag, avg_z_score, z_score_count in rows
    }
