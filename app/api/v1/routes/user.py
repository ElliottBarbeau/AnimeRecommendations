from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from decimal import Decimal
from statistics import pstdev
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import re
from app.api.deps import get_db
from app.db.models.user import User
from app.db.models.user_stats import UserStats
from app.db.models.anime import Anime
from app.db.models.user_anime_entry import UserAnimeEntry
from app.db.enums import AnimeStatus, AnimeType, EntryStatus, Provider
from app.schemas.user import UserCreate, UserRead, UserImportMALRequest, UserImportMALResponse

router = APIRouter(prefix="/users", tags=["User"])

_MAL_USERNAME_RE = re.compile(r"^/animelist/([^/]+?)/?$", re.IGNORECASE)
_MAL_LOAD_PAGE_SIZE = 300

def _parse_mal_username(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        if parsed.netloc.lower() not in {"myanimelist.net", "www.myanimelist.net"}:
            raise HTTPException(status_code=400, detail="mal_list_url must be a myanimelist.net URL")
        match = _MAL_USERNAME_RE.match(parsed.path)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid MAL list URL format")
        return match.group(1)

    if "/" in value or not value.strip():
        raise HTTPException(status_code=400, detail="Provide a valid MAL list URL or username")
    return value.strip()

def _fetch_json(url: str) -> object:
    req = Request(url, headers={"User-Agent": "AnimeRecommendations/1.0"})
    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""

        message = None
        if body:
            try:
                error_payload = json.loads(body)
                if isinstance(error_payload, dict):
                    maybe_message = error_payload.get("message")
                    if isinstance(maybe_message, str) and maybe_message.strip():
                        message = maybe_message.strip()
            except json.JSONDecodeError:
                message = None

        if exc.code == 404:
            raise HTTPException(status_code=404, detail="MAL user not found")
        if exc.code == 429:
            raise HTTPException(status_code=429, detail=message or "Jikan rate limit exceeded. Try again shortly.")
        raise HTTPException(status_code=502, detail=message or f"Upstream request failed: HTTP {exc.code}")
    except URLError:
        raise HTTPException(status_code=502, detail="Could not reach MAL/Jikan upstream")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Invalid JSON from MAL/Jikan upstream")

def _extract_mal_id_from_profile(profile_data: object) -> int | None:
    if not isinstance(profile_data, dict):
        return None

    data = profile_data.get("data")
    if not isinstance(data, dict):
        return None

    mal_id = data.get("mal_id")
    if isinstance(mal_id, int):
        return mal_id

    user_data = data.get("user")
    if isinstance(user_data, dict):
        nested_mal_id = user_data.get("mal_id")
        if isinstance(nested_mal_id, int):
            return nested_mal_id

    return None

def _fetch_provider_user_id(username: str) -> int:
    profile_data_basic = _fetch_json(f"https://api.jikan.moe/v4/users/{username}")
    mal_id = _extract_mal_id_from_profile(profile_data_basic)
    if mal_id is not None:
        return mal_id

    raise HTTPException(status_code=502, detail="Jikan profile response did not include MAL user id")

def _map_entry_status(status_code: int | None) -> EntryStatus:
    if status_code == 1:
        return EntryStatus.WATCHING
    if status_code == 2:
        return EntryStatus.WATCHED
    if status_code == 3:
        return EntryStatus.ON_HOLD
    if status_code == 4:
        return EntryStatus.DROPPED
    return EntryStatus.PLAN_TO_WATCH

def _map_anime_status(airing_status: int | None) -> AnimeStatus | None:
    if airing_status == 1:
        return AnimeStatus.AIRING
    if airing_status == 2:
        return AnimeStatus.COMPLETED
    if airing_status == 3:
        return AnimeStatus.ANNOUNCED
    return None

def _map_anime_type(value: str | None) -> AnimeType | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for anime_type in AnimeType:
        if anime_type.value == normalized:
            return anime_type
    return AnimeType.UNKNOWN

def _extract_year(value: str | None) -> int | None:
    if not value:
        return None
    parts = value.split("-")
    if len(parts) != 3:
        return None
    year_str = parts[2].strip()
    if not year_str.isdigit():
        return None
    if len(year_str) == 4:
        return int(year_str)
    if len(year_str) == 2:
        year_2 = int(year_str)
        return 1900 + year_2 if year_2 >= 70 else 2000 + year_2
    return None

def _pick_anime_title(item: dict) -> str | None:
    english_title = item.get("anime_title_eng")
    if isinstance(english_title, str) and english_title.strip():
        return english_title.strip()

    fallback_title = item.get("anime_title")
    if isinstance(fallback_title, str) and fallback_title.strip():
        return fallback_title.strip()

    return None

@router.get("/by-id/{id}", response_model=UserRead)
def get_user(id: int, db: Session=Depends(get_db)):
    user = db.execute(select(User).where(User.id == id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserRead)
def create_user(payload: UserCreate, db: Session=Depends(get_db)):
    existing = db.execute(
        select(User).where(User.provider == payload.provider, User.provider_username == payload.provider_username)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    user = User(**payload.model_dump())
    db.add(user)
    db.flush()
    db.add(UserStats(user_id=user.id, mean_score=0.0, stddev_score=0.0, rating_count=0))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    
    db.refresh(user)
    return user

@router.post("/import/mal", response_model=UserImportMALResponse)
def import_mal_list(payload: UserImportMALRequest, db: Session=Depends(get_db)):
    username = _parse_mal_username(payload.mal_list_url)
    provider_user_id = _fetch_provider_user_id(username)

    user = db.execute(
        select(User).where(User.provider == Provider.MAL, User.provider_username == username)
    ).scalar_one_or_none()

    users_created = 0
    users_updated = 0
    if user is None:
        user = User(
            provider=Provider.MAL,
            provider_username=username,
            provider_user_id=provider_user_id,
        )
        db.add(user)
        db.flush()
        db.add(UserStats(user_id=user.id, mean_score=0.0, stddev_score=0.0, rating_count=0))
        users_created = 1
    elif user.provider_user_id != provider_user_id:
        user.provider_user_id = provider_user_id
        users_updated = 1

    pages_fetched = 0
    items_seen = 0
    anime_created = 0
    anime_updated = 0
    entries_created = 0
    entries_updated = 0

    offset = 0
    while True:
        list_data = _fetch_json(
            f"https://myanimelist.net/animelist/{username}/load.json?offset={offset}&status=7"
        )
        if not isinstance(list_data, list):
            raise HTTPException(status_code=502, detail="Unexpected MAL list response shape")

        if not list_data:
            break

        pages_fetched += 1
        items_seen += len(list_data)

        for item in list_data:
            if not isinstance(item, dict):
                continue

            provider_anime_id = item.get("anime_id")
            title = _pick_anime_title(item)
            if not isinstance(provider_anime_id, int) or title is None:
                continue

            anime = db.execute(
                select(Anime).where(
                    Anime.provider == Provider.MAL,
                    Anime.provider_anime_id == provider_anime_id,
                )
            ).scalar_one_or_none()

            provider_rating = item.get("anime_score_val")
            rating_decimal = Decimal(str(provider_rating)) if isinstance(provider_rating, (int, float)) else None
            episode_count_raw = item.get("anime_num_episodes")
            episode_count = episode_count_raw if isinstance(episode_count_raw, int) and episode_count_raw > 0 else None

            anime_updates = {
                "title": title,
                "provider_rating": rating_decimal,
                "anime_type": _map_anime_type(item.get("anime_media_type_string")),
                "status": _map_anime_status(item.get("anime_airing_status")),
                "episode_count": episode_count,
                "start_year": _extract_year(item.get("anime_start_date_string")),
            }

            if anime is None:
                anime = Anime(
                    provider=Provider.MAL,
                    provider_anime_id=provider_anime_id,
                    **anime_updates,
                )
                db.add(anime)
                db.flush()
                anime_created += 1
            else:
                changed = False
                for key, value in anime_updates.items():
                    if getattr(anime, key) != value:
                        setattr(anime, key, value)
                        changed = True
                if changed:
                    anime_updated += 1

            entry = db.execute(
                select(UserAnimeEntry).where(
                    UserAnimeEntry.user_id == user.id,
                    UserAnimeEntry.anime_id == anime.id,
                )
            ).scalar_one_or_none()

            entry_updates = {
                "status": _map_entry_status(item.get("status")),
                "score": Decimal(str(item.get("score", 0))) if isinstance(item.get("score"), (int, float)) else None,
                "progress": item.get("num_watched_episodes") if isinstance(item.get("num_watched_episodes"), int) else None,
            }

            if entry is None:
                entry = UserAnimeEntry(user_id=user.id, anime_id=anime.id, **entry_updates)
                db.add(entry)
                entries_created += 1
            else:
                changed = False
                for key, value in entry_updates.items():
                    if getattr(entry, key) != value:
                        setattr(entry, key, value)
                        changed = True
                if changed:
                    entries_updated += 1

        offset += _MAL_LOAD_PAGE_SIZE

    user_scores = db.execute(
        select(UserAnimeEntry.score).where(
            UserAnimeEntry.user_id == user.id,
            UserAnimeEntry.score.is_not(None),
            UserAnimeEntry.score > 0,
        )
    ).scalars().all()
    score_values = [float(score) for score in user_scores]

    if score_values:
        mean_score = round(sum(score_values) / len(score_values), 4)
        stddev_score = round(pstdev(score_values), 4) if len(score_values) > 1 else 0.0
        rating_count = len(score_values)
    else:
        mean_score = 0.0
        stddev_score = 0.0
        rating_count = 0

    stats = db.execute(select(UserStats).where(UserStats.user_id == user.id)).scalar_one_or_none()
    if stats is None:
        stats = UserStats(user_id=user.id, mean_score=mean_score, stddev_score=stddev_score, rating_count=rating_count)
        db.add(stats)
        users_updated += 1
    elif (
        stats.mean_score != mean_score
        or stats.stddev_score != stddev_score
        or stats.rating_count != rating_count
    ):
        stats.mean_score = mean_score
        stats.stddev_score = stddev_score
        stats.rating_count = rating_count
        users_updated += 1

    user_entries = db.execute(
        select(UserAnimeEntry).where(UserAnimeEntry.user_id == user.id)
    ).scalars().all()
    for user_entry in user_entries:
        if user_entry.score is None or user_entry.score <= 0:
            calculated_z_score = None
        elif stddev_score > 0:
            calculated_z_score = round((float(user_entry.score) - mean_score) / stddev_score, 4)
        else:
            calculated_z_score = 0.0

        if user_entry.z_score != calculated_z_score:
            user_entry.z_score = calculated_z_score

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Import failed due to conflicting data")

    return UserImportMALResponse(
        provider=Provider.MAL,
        provider_username=username,
        provider_user_id=provider_user_id,
        pages_fetched=pages_fetched,
        items_seen=items_seen,
        users_created=users_created,
        users_updated=users_updated,
        anime_created=anime_created,
        anime_updated=anime_updated,
        entries_created=entries_created,
        entries_updated=entries_updated,
        mean_score=user.mean_score,
        stddev_score=user.stddev_score,
        rating_count=user.rating_count,
    )
