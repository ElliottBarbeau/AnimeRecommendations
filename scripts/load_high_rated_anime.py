import argparse
import json
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.db.enums import AnimeStatus, AnimeType, Provider
from app.db.models.anime import Anime
from app.db.session import SessionLocal


def fetch_json(url: str, retries: int = 4) -> object:
    req = Request(url, headers={"User-Agent": "AnimeRecommendations/1.0"})
    attempt = 0
    while True:
        try:
            with urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                attempt += 1
                time.sleep(1.5 * attempt)
                continue
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            message = f"HTTP {exc.code}"
            if body:
                try:
                    payload = json.loads(body)
                    if isinstance(payload, dict) and isinstance(payload.get("message"), str):
                        message = payload["message"]
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(f"Failed request to {url}: {message}") from exc
        except URLError as exc:
            raise RuntimeError(f"Failed request to {url}: {exc}") from exc


def map_anime_type(value: str | None) -> AnimeType | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for anime_type in AnimeType:
        if anime_type.value == normalized:
            return anime_type
    return AnimeType.UNKNOWN


def map_anime_status(value: str | None) -> AnimeStatus | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized == "currently airing":
        return AnimeStatus.AIRING
    if normalized == "finished airing":
        return AnimeStatus.COMPLETED
    if normalized == "not yet aired":
        return AnimeStatus.ANNOUNCED
    return None


def pick_title(item: dict) -> str | None:
    title_english = item.get("title_english")
    if isinstance(title_english, str) and title_english.strip():
        return title_english.strip()

    title_default = item.get("title")
    if isinstance(title_default, str) and title_default.strip():
        return title_default.strip()

    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load top-rated MAL anime (via Jikan) into local anime table."
    )
    parser.add_argument("--min-score", type=float, default=8.0, help="Minimum MAL score to keep.")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Max top/anime pages to scan before stopping.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.45,
        help="Delay between page requests to avoid rate limiting.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    pages_fetched = 0
    seen = 0
    created = 0
    updated = 0
    anime_cache: dict[int, Anime] = {}

    try:
        for page in range(1, args.max_pages + 1):
            url = f"https://api.jikan.moe/v4/top/anime?page={page}"
            payload = fetch_json(url)
            if not isinstance(payload, dict):
                raise RuntimeError(f"Unexpected response shape at page {page}")

            data = payload.get("data")
            if not isinstance(data, list) or not data:
                break

            pages_fetched += 1
            all_below_threshold = True

            for item in data:
                if not isinstance(item, dict):
                    continue

                score = item.get("score")
                if not isinstance(score, (int, float)):
                    continue
                if score < args.min_score:
                    continue

                all_below_threshold = False
                seen += 1

                mal_id = item.get("mal_id")
                title = pick_title(item)
                if not isinstance(mal_id, int) or title is None:
                    continue

                year = item.get("year")
                if not isinstance(year, int):
                    year = None

                episodes = item.get("episodes")
                if not isinstance(episodes, int) or episodes <= 0:
                    episodes = None

                values = {
                    "title": title,
                    "provider": Provider.MAL,
                    "provider_anime_id": mal_id,
                    "provider_rating": Decimal(str(score)),
                    "anime_type": map_anime_type(item.get("type")),
                    "status": map_anime_status(item.get("status")),
                    "episode_count": episodes,
                    "start_year": year,
                }

                existing = anime_cache.get(mal_id)
                if existing is None:
                    existing = db.execute(
                        select(Anime).where(
                            Anime.provider == Provider.MAL,
                            Anime.provider_anime_id == mal_id,
                        )
                    ).scalar_one_or_none()
                    if existing is not None:
                        anime_cache[mal_id] = existing

                if existing is None:
                    existing = Anime(**values)
                    db.add(existing)
                    anime_cache[mal_id] = existing
                    created += 1
                else:
                    changed = False
                    for key, value in values.items():
                        if key in {"provider", "provider_anime_id"}:
                            continue
                        if getattr(existing, key) != value:
                            setattr(existing, key, value)
                            changed = True
                    if changed:
                        updated += 1

            has_next_page = (
                isinstance(payload.get("pagination"), dict)
                and bool(payload["pagination"].get("has_next_page"))
            )

            # Because results are sorted by top score, once a full page is below threshold we can stop.
            if all_below_threshold or not has_next_page:
                break

            time.sleep(args.sleep_seconds)

        db.commit()
        print(
            f"Done. pages_fetched={pages_fetched} seen_above_threshold={seen} "
            f"created={created} updated={updated} min_score={args.min_score}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
