from collections import Counter
from app.db.session import SessionLocal
from app.db.repositories.user_anime_entries import (
    get_entries_above_z_score, 
    get_neighbours, 
    get_candidate_shows,
    get_average_rating_by_tag
)
from app.db.repositories.anime import (
    get_anime_title_by_id,
    get_anime_tags
)

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

        for id in list(counter.keys()):
            base_score = counter[id] * 0.55
            tags = get_anime_tags(db, id)
            tag_scores = []
            for tag in tags:
                avg = get_average_rating_by_tag(db, user_id, tag)
                if avg is not None:
                    tag_scores.append(float(avg))

            avg_tag_score = (sum(tag_scores) / len(tag_scores)) if tag_scores else 0.0
            genre_multiplier = z_bucket(avg_tag_score)
            base_score *= genre_multiplier
            counter[id] = base_score

        top_30 = counter.most_common(30)
        for id, score in top_30:
            print(f"{get_anime_title_by_id(db, id)}: {round(score, 2)}")

    finally:
        db.close()
    

if __name__ == "__main__":
    recommend_for_user(4, 1.0)
