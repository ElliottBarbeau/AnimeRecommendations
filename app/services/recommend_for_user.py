from collections import Counter
from app.db.session import SessionLocal
from app.db.repositories.user_anime_entries import (
    get_entries_above_z_score, 
    get_neighbours, 
    get_candidate_shows,
    get_user_tag_preferences,
)
from app.db.repositories.anime import (
    get_anime_metadata_by_ids,
)
from app.db.repositories.tag_similarity import get_similarity_scores_for_tag_pairs

# discovery tuning
RELATED_TAG_SIMILARITY_THRESHOLD = 0.20
RELATED_DISCOVERY_MULTIPLIER = 1.05
MIN_CONFIDENT_TAG_COUNT = 2

def z_bucket(z: float | None) -> float:
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
        

def recommend_for_user(user_id, z_score):
    # changed score instances to z-score, which is normalized score to get better data
    # target user's z_score >= 1.0 shows
    # neighbour users who also gave those shows z_score >= 1.0
    # candidate shows are the ones that neighbours scored z_score >= 1.0
    # exclude shows target user already has in their list
    # simple scoring for now, just +1

    # +1 every time a neighbour has z_score >= 1.0
    # sort by descending score


    # cap how much one neighbour can contribute?
    # minimum 2 supporting neighbours for a candidate
    # some things to consider
    # 1. adding tags
    # -> if someone doesn't watch shounen, they prob don't want to watch CSM Reze arc, even though its very high rated
    # -> people with heavy psychological pref would probably like to stick to that genre (for example)

    db = SessionLocal()
    try:
        user_shows = get_entries_above_z_score(db, user_id, z_score)
        neighbours = get_neighbours(db, user_shows, user_id, z_score)
        candidate_shows = get_candidate_shows(db, neighbours, user_id, z_score)
        counter = Counter(candidate_shows)
        user_tag_prefs = get_user_tag_preferences(db, user_id)
        anime_metadata_by_id = get_anime_metadata_by_ids(db, list(counter.keys()))
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

        for id in list(counter.keys()):
            anime_meta = anime_metadata_by_id.get(id)
            if anime_meta is None:
                continue

            base_score = counter[id] * 0.55
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
            genre_multiplier = z_bucket(avg_tag_score)

            if liked_known_tags and unknown_tags and not has_strong_disliked_tag:
                has_related_unknown_tag = any(
                    similarity_scores_by_pair.get((liked_tag, unknown_tag), 0.0) >= RELATED_TAG_SIMILARITY_THRESHOLD
                    for liked_tag in liked_known_tags
                    for unknown_tag in unknown_tags
                )
                if has_related_unknown_tag:
                    genre_multiplier *= RELATED_DISCOVERY_MULTIPLIER

            base_score *= genre_multiplier
            counter[id] = base_score


        top_30 = counter.most_common(30)
        for id, score in top_30:
            title = anime_metadata_by_id.get(id, {}).get("title", f"Anime {id}")
            print(f"{title}: {round(score, 2)}")

    finally:
        db.close()
    

if __name__ == "__main__":
    recommend_for_user(1, 1.0)
