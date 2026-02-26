from collections import Counter
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.anime import Anime
from app.db.models.mal_relation_cache import MalRelationCache
from app.db.models.user_anime_entry import UserAnimeEntry
from app.db.repositories.user_anime_entries import (
    get_entries_above_z_score, 
    get_neighbours, 
    get_candidate_shows,
    get_user_tag_preferences,
)
from app.db.repositories.anime import (
    get_anime_metadata_by_ids,
    get_anime_metadata_by_mal_ids,
    get_mal_franchise_nodes_by_mal_ids,
)
from app.db.enums import Provider
from app.db.repositories.tag_similarity import get_similarity_scores_for_tag_pairs
from app.services.mal_franchise_resolver import MalFranchiseResolver
from app.schemas.recommendations import RecommendationItem

# discovery tuning
RELATED_TAG_SIMILARITY_THRESHOLD = 0.20
RELATED_DISCOVERY_MAX_BONUS = 0.15
RELATED_DISCOVERY_STRENGTH = 0.25
MIN_CONFIDENT_TAG_COUNT = 2
MIN_CANDIDATE_SUPPORT_COUNT = 10
OUTPUT_RESOLUTION_POOL_SIZE = 120
FRANCHISE_COLLAPSE_POOL_SIZE = 20
FINAL_RECOMMENDATION_COUNT = 10
FRANCHISE_COLLAPSE_EXPANSION_STEP = 10
FRANCHISE_RELATION_BACKFILL_MAX_CANDIDATES = 50
FRANCHISE_RELATION_BACKFILL_TOP_CANDIDATES = 15
JIKAN_RELATIONS_MIN_INTERVAL_SECONDS = 0.7
JIKAN_RELATIONS_MAX_RETRIES = 3
_last_jikan_relations_request_at = 0.0
_LIKELY_CONTINUATION_TITLE_RE = re.compile(
    r"(?ix)"
    r"("
    r"\bseason\s+\d+\b|"
    r"\bpart\s+\d+\b|"
    r"\b\d+(st|nd|rd|th)\s+season\b|"
    r"\bfinal\s+season\b|"
    r"\bcour\s+\d+\b|"
    r"\b[2-9]\d{0,1}\b$|"
    r"\bii\b|\biii\b|\biv\b|\bv\b|\bvi\b|\bvii\b|\bviii\b|\bix\b|\bx\b|"
    r"\b2nd\b|\b3rd\b|\b4th\b|\b5th\b"
    r")"
)

def _z_bucket(z: float | None) -> float:
    match z:
        case None:
            return 1
        case value if value >= 0.5:
            return 1.25
        case value if value >= 0.2:
            return 1.15
        case value if value > -0.2:
            return 1
        case value if value > -0.5:
            return 0.9
        case _:
            return 0.75


def _throttle_jikan_relations_requests() -> None:
    global _last_jikan_relations_request_at
    elapsed = time.monotonic() - _last_jikan_relations_request_at
    wait_seconds = JIKAN_RELATIONS_MIN_INTERVAL_SECONDS - elapsed
    if wait_seconds > 0:
        time.sleep(wait_seconds)


def _mark_jikan_relations_request_complete() -> None:
    global _last_jikan_relations_request_at
    _last_jikan_relations_request_at = time.monotonic()


def _extract_prequel_sequel_relation_ids(payload: object) -> list[int]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []

    related_ids: set[int] = set()
    for relation in data:
        if not isinstance(relation, dict):
            continue
        relation_name = str(relation.get("relation", "")).strip().lower()
        if relation_name not in {"prequel", "sequel"}:
            continue

        entries = relation.get("entry")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("type", "")).strip().lower() != "anime":
                continue
            mal_id = entry.get("mal_id")
            if isinstance(mal_id, int):
                related_ids.add(mal_id)

    return sorted(related_ids)


def _looks_like_continuation_title(title: str | None) -> bool:
    if not isinstance(title, str):
        return False
    normalized = title.strip()
    if not normalized:
        return False
    return bool(_LIKELY_CONTINUATION_TITLE_RE.search(normalized))


def _fetch_jikan_relations_for_mal_id(mal_id: int) -> list[int] | None:
    url = f"https://api.jikan.moe/v4/anime/{mal_id}/relations"
    attempts = 0

    while True:
        _throttle_jikan_relations_requests()
        started = time.perf_counter()
        try:
            req = Request(url, headers={"User-Agent": "AnimeRecommendations/1.0"})
            with urlopen(req, timeout=20) as response:
                _mark_jikan_relations_request_complete()
                payload = json.loads(response.read().decode("utf-8"))
                _ = time.perf_counter() - started
                return _extract_prequel_sequel_relation_ids(payload)
        except HTTPError as exc:
            _mark_jikan_relations_request_complete()
            if exc.code == 404:
                return []
            if exc.code == 429 and attempts < JIKAN_RELATIONS_MAX_RETRIES:
                attempts += 1
                time.sleep(1.5 * (2 ** (attempts - 1)))
                continue
            return None
        except (URLError, json.JSONDecodeError):
            if attempts < JIKAN_RELATIONS_MAX_RETRIES:
                attempts += 1
                time.sleep(1.5 * (2 ** (attempts - 1)))
                continue
            return None


def _seed_candidate_mal_ids(
    ranked_candidates,
    anime_metadata_by_id,
    *,
    likely_continuations_only: bool = False,
    max_count: int | None = None,
) -> list[int]:
    seed_mal_ids: list[int] = []
    seen: set[int] = set()
    for anime_id, _score in ranked_candidates:
        anime_meta = anime_metadata_by_id.get(anime_id)
        if anime_meta is None:
            continue
        if anime_meta.get("provider") != Provider.MAL:
            continue
        mal_id = anime_meta.get("provider_anime_id")
        if not isinstance(mal_id, int):
            continue
        if likely_continuations_only and not _looks_like_continuation_title(anime_meta.get("title")):
            continue
        if mal_id in seen:
            continue
        seen.add(mal_id)
        seed_mal_ids.append(mal_id)
        if max_count is not None and len(seed_mal_ids) >= max_count:
            break
    return seed_mal_ids


def _seed_relation_backfill_mal_ids(ranked_candidates, anime_metadata_by_id) -> list[int]:
    # Seed with top candidates regardless of title (captures titles like "Zoku Owarimonogatari"),
    # then add likely continuation titles from a wider pool.
    primary = _seed_candidate_mal_ids(
        ranked_candidates,
        anime_metadata_by_id,
        likely_continuations_only=False,
        max_count=FRANCHISE_RELATION_BACKFILL_TOP_CANDIDATES,
    )
    heuristic = _seed_candidate_mal_ids(
        ranked_candidates,
        anime_metadata_by_id,
        likely_continuations_only=True,
        max_count=FRANCHISE_RELATION_BACKFILL_MAX_CANDIDATES,
    )

    combined: list[int] = []
    seen: set[int] = set()
    for mal_id in primary + heuristic:
        if mal_id in seen:
            continue
        seen.add(mal_id)
        combined.append(mal_id)
    return combined


def _load_cached_franchise_roots_for_ranked_pool(db, ranked_candidates, anime_metadata_by_id) -> dict[int, int]:
    candidate_mal_ids = _seed_candidate_mal_ids(ranked_candidates, anime_metadata_by_id)
    if not candidate_mal_ids:
        return {}

    rows = db.execute(
        select(
            Anime.provider_anime_id,
            Anime.franchise_root_mal_id,
            Anime.related_prequel_sequel_mal_ids,
        ).where(
            Anime.provider == Provider.MAL,
            Anime.provider_anime_id.in_(candidate_mal_ids),
            Anime.franchise_root_mal_id.is_not(None),
        )
    ).all()

    cached: dict[int, int] = {}
    for mal_id, root_mal_id, related_ids in rows:
        if not isinstance(mal_id, int) or not isinstance(root_mal_id, int) or root_mal_id <= 0:
            continue
        has_relations = isinstance(related_ids, list) and any(isinstance(v, int) for v in related_ids)
        # Ignore stale "self root" cache values when we still have no relation data;
        # those are unresolved placeholders and should not block future backfills.
        if root_mal_id == mal_id and not has_relations:
            continue
        cached[mal_id] = root_mal_id
    return cached


def _ensure_franchise_relations_for_ranked_pool(db, ranked_candidates, anime_metadata_by_id):
    seed_mal_ids = _seed_relation_backfill_mal_ids(ranked_candidates, anime_metadata_by_id)
    if not seed_mal_ids:
        return {}, False

    rows = db.execute(
        select(Anime).where(
            Anime.provider == Provider.MAL,
            Anime.provider_anime_id.in_(seed_mal_ids),
        )
    ).scalars().all()
    anime_by_mal_id = {row.provider_anime_id: row for row in rows}
    cache_rows = db.execute(
        select(MalRelationCache).where(MalRelationCache.provider_anime_id.in_(seed_mal_ids))
    ).scalars().all()
    relation_cache_by_mal_id = {row.provider_anime_id: row for row in cache_rows}

    stack = list(seed_mal_ids)
    visited: set[int] = set()
    runtime_nodes_by_mal_id: dict[int, dict[str, object]] = {}
    touched_rows = False

    while stack:
        current_mal_id = stack.pop()
        if current_mal_id in visited:
            continue
        visited.add(current_mal_id)

        anime_row = anime_by_mal_id.get(current_mal_id)
        if anime_row is None:
            cache_row = relation_cache_by_mal_id.get(current_mal_id)
            if cache_row is None:
                cache_row = db.execute(
                    select(MalRelationCache).where(MalRelationCache.provider_anime_id == current_mal_id)
                ).scalar_one_or_none()
                if cache_row is not None:
                    relation_cache_by_mal_id[current_mal_id] = cache_row
            if cache_row is not None:
                relation_ids = [
                    value for value in (cache_row.related_prequel_sequel_mal_ids or []) if isinstance(value, int)
                ]
            else:
                relation_ids = _fetch_jikan_relations_for_mal_id(current_mal_id)
                if relation_ids is None:
                    continue
                cache_row = MalRelationCache(
                    provider_anime_id=current_mal_id,
                    related_prequel_sequel_mal_ids=relation_ids,
                )
                db.add(cache_row)
                relation_cache_by_mal_id[current_mal_id] = cache_row
                touched_rows = True

            runtime_nodes_by_mal_id[current_mal_id] = {
                "provider_anime_id": current_mal_id,
                "related_prequel_sequel_mal_ids": relation_ids,
            }
            for related_id in relation_ids:
                if related_id not in visited:
                    stack.append(related_id)
                if related_id not in relation_cache_by_mal_id and related_id not in anime_by_mal_id:
                    cached_related = db.execute(
                        select(MalRelationCache).where(MalRelationCache.provider_anime_id == related_id)
                    ).scalar_one_or_none()
                    if cached_related is not None:
                        relation_cache_by_mal_id[related_id] = cached_related
            continue

        existing_related = [value for value in (anime_row.related_prequel_sequel_mal_ids or []) if isinstance(value, int)]
        if (
            isinstance(anime_row.franchise_root_mal_id, int)
            and anime_row.franchise_root_mal_id > 0
            and existing_related
        ):
            # Root cache + relation links already exist; skip network backfill.
            for related_id in existing_related:
                if related_id not in visited:
                    stack.append(related_id)
            continue
        if existing_related:
            for related_id in existing_related:
                if related_id not in visited:
                    stack.append(related_id)
            continue

        relation_ids = _fetch_jikan_relations_for_mal_id(current_mal_id)
        if relation_ids is None:
            continue

        anime_row.related_prequel_sequel_mal_ids = relation_ids
        touched_rows = True
        for related_id in relation_ids:
            if related_id not in visited:
                stack.append(related_id)

            if related_id not in anime_by_mal_id:
                related_row = db.execute(
                    select(Anime).where(
                        Anime.provider == Provider.MAL,
                        Anime.provider_anime_id == related_id,
                    )
                ).scalar_one_or_none()
                if related_row is not None:
                    anime_by_mal_id[related_id] = related_row
                elif related_id not in relation_cache_by_mal_id:
                    cached_related = db.execute(
                        select(MalRelationCache).where(MalRelationCache.provider_anime_id == related_id)
                    ).scalar_one_or_none()
                    if cached_related is not None:
                        relation_cache_by_mal_id[related_id] = cached_related

    if touched_rows:
        db.flush()

    return runtime_nodes_by_mal_id, touched_rows


def _collapse_output_to_franchise_entrypoints(db, ranked_candidates, anime_metadata_by_id, runtime_nodes_by_mal_id=None):
    runtime_nodes_by_mal_id = runtime_nodes_by_mal_id or {}
    cached_roots_by_mal_id = _load_cached_franchise_roots_for_ranked_pool(db, ranked_candidates, anime_metadata_by_id)

    def _load_franchise_nodes(mal_ids: list[int]) -> dict[int, dict[str, object]]:
        db_nodes = get_mal_franchise_nodes_by_mal_ids(db, mal_ids)
        loaded: dict[int, dict[str, object]] = dict(db_nodes)
        for mal_id in mal_ids:
            if mal_id not in loaded and mal_id in runtime_nodes_by_mal_id:
                loaded[mal_id] = runtime_nodes_by_mal_id[mal_id]
        return loaded

    resolver = MalFranchiseResolver(_load_franchise_nodes)
    aggregated_scores = Counter()
    display_meta_by_id: dict[int, dict] = {}
    needed_root_mal_ids: set[int] = set()
    candidate_root_mal_id_by_local_id: dict[int, int] = {}

    for anime_id, _score in ranked_candidates:
        anime_meta = anime_metadata_by_id.get(anime_id)
        if anime_meta is None:
            continue

        provider = anime_meta.get("provider")
        mal_id = anime_meta.get("provider_anime_id")
        if provider != Provider.MAL or not isinstance(mal_id, int):
            candidate_root_mal_id_by_local_id[anime_id] = -1
            continue

        cached_root_mal_id = cached_roots_by_mal_id.get(mal_id)
        if isinstance(cached_root_mal_id, int) and cached_root_mal_id > 0:
            resolved_mal_id = cached_root_mal_id
        else:
            resolved_mal_id = resolver.resolve_entrypoint(mal_id)
        candidate_root_mal_id_by_local_id[anime_id] = resolved_mal_id
        if resolved_mal_id != mal_id:
            needed_root_mal_ids.add(resolved_mal_id)

    root_meta_by_mal_id = get_anime_metadata_by_mal_ids(db, list(needed_root_mal_ids))

    for anime_id, score in ranked_candidates:
        anime_meta = anime_metadata_by_id.get(anime_id)
        if anime_meta is None:
            continue

        resolved_mal_id = candidate_root_mal_id_by_local_id.get(anime_id)
        resolved_root_meta = (
            root_meta_by_mal_id.get(resolved_mal_id)
            if isinstance(resolved_mal_id, int) and resolved_mal_id > 0
            else None
        )

        if resolved_root_meta is not None and isinstance(resolved_root_meta.get("id"), int):
            canonical_id = resolved_root_meta["id"]
            canonical_meta = {
                "title": resolved_root_meta.get("title"),
                "tags": resolved_root_meta.get("tags") or [],
                "provider": resolved_root_meta.get("provider"),
                "provider_anime_id": resolved_root_meta.get("provider_anime_id"),
                "anime_type": resolved_root_meta.get("anime_type"),
                "provider_rating": resolved_root_meta.get("provider_rating"),
                "start_year": resolved_root_meta.get("start_year"),
            }
        else:
            canonical_id = anime_id
            canonical_meta = anime_meta

        if canonical_id not in aggregated_scores or score > aggregated_scores[canonical_id]:
            aggregated_scores[canonical_id] = score
        display_meta_by_id.setdefault(canonical_id, canonical_meta)

    cache_updates = _persist_franchise_root_cache_for_ranked_pool(
        db,
        ranked_candidates,
        anime_metadata_by_id,
        candidate_root_mal_id_by_local_id,
    )

    return aggregated_scores, display_meta_by_id, cache_updates


def _persist_franchise_root_cache_for_ranked_pool(db, ranked_candidates, anime_metadata_by_id, candidate_root_mal_id_by_local_id) -> bool:
    desired_roots_by_mal_id: dict[int, int] = {}
    for anime_id, _score in ranked_candidates:
        anime_meta = anime_metadata_by_id.get(anime_id)
        if anime_meta is None or anime_meta.get("provider") != Provider.MAL:
            continue
        mal_id = anime_meta.get("provider_anime_id")
        if not isinstance(mal_id, int):
            continue
        resolved_root = candidate_root_mal_id_by_local_id.get(anime_id)
        if not isinstance(resolved_root, int) or resolved_root <= 0:
            continue
        desired_roots_by_mal_id[mal_id] = resolved_root

    if not desired_roots_by_mal_id:
        return False

    rows = db.execute(
        select(Anime).where(
            Anime.provider == Provider.MAL,
            Anime.provider_anime_id.in_(list(desired_roots_by_mal_id.keys())),
        )
    ).scalars().all()

    touched = False
    for row in rows:
        desired_root = desired_roots_by_mal_id.get(row.provider_anime_id)
        if desired_root is None:
            continue
        existing_related = [value for value in (row.related_prequel_sequel_mal_ids or []) if isinstance(value, int)]
        if desired_root == row.provider_anime_id and not existing_related:
            continue
        if row.franchise_root_mal_id != desired_root:
            row.franchise_root_mal_id = desired_root
            touched = True

    if touched:
        db.flush()
    return touched


def recommend_for_user(db, user_id, z_score=0.25):
    user_shows = get_entries_above_z_score(db, user_id, z_score)
    neighbours = get_neighbours(db, user_shows, user_id, z_score)
    candidate_shows = get_candidate_shows(db, neighbours, user_id, z_score)
    score_dict = Counter(
        {
            row["anime_id"]: row["base_score"]
            for row in candidate_shows
            if row["support_count"] >= MIN_CANDIDATE_SUPPORT_COUNT
        }
    )
    user_tag_prefs = get_user_tag_preferences(db, user_id)
    anime_metadata_by_id = get_anime_metadata_by_ids(db, list(score_dict.keys()))
    global_liked_tags = [
        tag
        for tag, pref in user_tag_prefs.items()
        if pref["avg_z_score"] is not None
        and pref["z_score_count"] >= MIN_CONFIDENT_TAG_COUNT
        and float(pref["avg_z_score"]) >= 0.2
    ]
    all_unknown_candidate_tags = sorted(
        {
            tag
            for anime_meta in anime_metadata_by_id.values()
            for tag in (anime_meta.get("tags") or [])
            if tag not in user_tag_prefs
        }
    )
    similarity_scores_by_pair = get_similarity_scores_for_tag_pairs(
        db,
        global_liked_tags,
        all_unknown_candidate_tags,
        min_cooccurrence_count=2,
    )

    for id in list(score_dict.keys()):
        anime_meta = anime_metadata_by_id.get(id)
        if anime_meta is None:
            continue

        base_score = score_dict[id] * 0.55
        tags = anime_meta["tags"]
        known_scores: list[float] = []
        liked_known_tags: list[str] = []
        unknown_tags: list[str] = []
        has_strong_disliked_tag = False

        for tag in tags:
            pref = user_tag_prefs.get(tag)
            if pref is None or pref["avg_z_score"] is None:
                unknown_tags.append(tag)
                continue

            avg_z = float(pref["avg_z_score"])
            known_scores.append(avg_z)

            if pref["z_score_count"] >= MIN_CONFIDENT_TAG_COUNT:
                if avg_z >= 0.2:
                    liked_known_tags.append(tag)
                if avg_z <= -0.5:
                    has_strong_disliked_tag = True

        avg_tag_score = (sum(known_scores) / len(known_scores)) if known_scores else 0.0
        genre_multiplier = _z_bucket(avg_tag_score)

        if liked_known_tags and unknown_tags and not has_strong_disliked_tag:
            best_similarity = max(
                (
                    similarity_scores_by_pair.get((liked_tag, unknown_tag), 0.0)
                    for liked_tag in liked_known_tags
                    for unknown_tag in unknown_tags
                ),
                default=0.0,
            )
            if best_similarity >= RELATED_TAG_SIMILARITY_THRESHOLD:
                discovery_multiplier = 1.0 + min(
                    RELATED_DISCOVERY_MAX_BONUS,
                    best_similarity * RELATED_DISCOVERY_STRENGTH,
                )
                genre_multiplier *= discovery_multiplier

        base_score *= genre_multiplier
        score_dict[id] = base_score

    user_seen_anime_ids = set(
        db.execute(
            select(UserAnimeEntry.anime_id).where(UserAnimeEntry.user_id == user_id)
        ).scalars().all()
    )

    ranked_pool = score_dict.most_common(OUTPUT_RESOLUTION_POOL_SIZE)
    collapse_pool_size = min(FRANCHISE_COLLAPSE_POOL_SIZE, len(ranked_pool))
    any_relations_cache_updated = False
    any_franchise_cache_updated = False
    display_scores = Counter()
    display_metadata_by_id: dict[int, dict] = {}

    while collapse_pool_size > 0:
        franchise_pool = ranked_pool[:collapse_pool_size]
        runtime_franchise_nodes, relations_cache_updated = _ensure_franchise_relations_for_ranked_pool(
            db,
            franchise_pool,
            anime_metadata_by_id,
        )
        display_scores, display_metadata_by_id, franchise_cache_updated = _collapse_output_to_franchise_entrypoints(
            db,
            franchise_pool,
            anime_metadata_by_id,
            runtime_franchise_nodes,
        )
        any_relations_cache_updated = any_relations_cache_updated or relations_cache_updated
        any_franchise_cache_updated = any_franchise_cache_updated or franchise_cache_updated

        available_count = 0
        for anime_id, _score in display_scores.most_common(collapse_pool_size):
            if anime_id in user_seen_anime_ids:
                continue
            available_count += 1
            if available_count >= FINAL_RECOMMENDATION_COUNT:
                break

        if available_count >= FINAL_RECOMMENDATION_COUNT or collapse_pool_size >= len(ranked_pool):
            break

        collapse_pool_size = min(len(ranked_pool), collapse_pool_size + FRANCHISE_COLLAPSE_EXPANSION_STEP)

    if any_relations_cache_updated or any_franchise_cache_updated:
        db.commit()

    recommendation_items = []
    for id, match_score in display_scores.most_common(collapse_pool_size):
        if id in user_seen_anime_ids:
            continue
        item = RecommendationItem(
            title=display_metadata_by_id.get(id, {}).get("title", f"Anime {id}"),
            score=match_score
        )
        recommendation_items.append(item)
        if len(recommendation_items) >= FINAL_RECOMMENDATION_COUNT:
            break

    return recommendation_items
