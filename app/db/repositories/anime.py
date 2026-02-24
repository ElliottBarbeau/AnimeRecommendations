from app.db.models.anime import Anime
from sqlalchemy import select
from app.db.enums import Provider

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
        select(
            Anime.id,
            Anime.title,
            Anime.tags,
            Anime.provider,
            Anime.provider_anime_id,
            Anime.anime_type,
            Anime.provider_rating,
            Anime.provider_popularity_rank,
            Anime.provider_member_count,
            Anime.start_year,
        )
        .where(Anime.id.in_(anime_ids))
    ).all()

    return {
        anime_id: {
            "title": title,
            "tags": tags or [],
            "provider": provider,
            "provider_anime_id": provider_anime_id,
            "anime_type": anime_type,
            "provider_rating": (float(provider_rating) if provider_rating is not None else None),
            "provider_popularity_rank": provider_popularity_rank,
            "provider_member_count": provider_member_count,
            "start_year": start_year,
        }
        for (
            anime_id,
            title,
            tags,
            provider,
            provider_anime_id,
            anime_type,
            provider_rating,
            provider_popularity_rank,
            provider_member_count,
            start_year,
        ) in rows
    }


def get_anime_metadata_by_mal_ids(db, mal_ids: list[int]):
    if not mal_ids:
        return {}

    rows = db.execute(
        select(
            Anime.id,
            Anime.title,
            Anime.tags,
            Anime.provider,
            Anime.provider_anime_id,
            Anime.anime_type,
            Anime.provider_rating,
            Anime.provider_popularity_rank,
            Anime.provider_member_count,
            Anime.start_year,
        )
        .where(
            Anime.provider == Provider.MAL,
            Anime.provider_anime_id.in_(mal_ids),
        )
    ).all()

    return {
        provider_anime_id: {
            "id": anime_id,
            "title": title,
            "tags": tags or [],
            "provider": provider,
            "provider_anime_id": provider_anime_id,
            "anime_type": anime_type,
            "provider_rating": (float(provider_rating) if provider_rating is not None else None),
            "provider_popularity_rank": provider_popularity_rank,
            "provider_member_count": provider_member_count,
            "start_year": start_year,
        }
        for (
            anime_id,
            title,
            tags,
            provider,
            provider_anime_id,
            anime_type,
            provider_rating,
            provider_popularity_rank,
            provider_member_count,
            start_year,
        ) in rows
    }


def get_mal_franchise_nodes_by_mal_ids(db, mal_ids: list[int]):
    if not mal_ids:
        return {}

    rows = db.execute(
        select(
            Anime.id,
            Anime.title,
            Anime.provider_anime_id,
            Anime.anime_type,
            Anime.provider_rating,
            Anime.provider_popularity_rank,
            Anime.provider_member_count,
            Anime.start_year,
            Anime.related_prequel_sequel_mal_ids,
        )
        .where(
            Anime.provider == Provider.MAL,
            Anime.provider_anime_id.in_(mal_ids),
        )
    ).all()

    return {
        provider_anime_id: {
            "id": anime_id,
            "title": title,
            "provider_anime_id": provider_anime_id,
            "anime_type": anime_type,
            "provider_rating": (float(provider_rating) if provider_rating is not None else None),
            "provider_popularity_rank": provider_popularity_rank,
            "provider_member_count": provider_member_count,
            "start_year": start_year,
            "related_prequel_sequel_mal_ids": related_prequel_sequel_mal_ids or [],
        }
        for (
            anime_id,
            title,
            provider_anime_id,
            anime_type,
            provider_rating,
            provider_popularity_rank,
            provider_member_count,
            start_year,
            related_prequel_sequel_mal_ids,
        ) in rows
    }
