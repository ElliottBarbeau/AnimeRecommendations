from collections import Counter
from app.db.session import SessionLocal
from app.db.repositories.user_anime_entries import (
    get_entries_above_score, 
    get_neighbours, 
    get_candidate_shows
)
from app.db.repositories.anime import get_anime_title_by_id

def recommend_for_user(user_id):
    # target user's score >= 8.0 shows
    # neighbour users who also gave those shows >= 8.0
    # candidate shows are the ones that the neighbour scored >= 8.0
    # exclude shows target user already has in their list
    # simple scoring for now, just +1

    # +1 every time a neighbour rated it >= 8.0
    # sort by descending score


    # cap how much one neighbour can contribute?
    # minimum 2 supporting neighbours for a candidate
    # some things to consider
    # 1. adding tags
    # -> if someone doesn't watch shounen, they prob don't want to watch CSM Reze arc, even though its very high rated
    # -> people with heavy psychological pref would probably like to stick to that genre (for example)

    db = SessionLocal()
    try:
        user_shows = get_entries_above_score(db, user_id, 9)
        neighbours = get_neighbours(db, user_shows, user_id, 9)
        candidate_shows = get_candidate_shows(db, neighbours, user_id, 9)
    finally:
        db.close()
        
    print(user_shows)
    print(neighbours)

    top_20 = Counter(candidate_shows).most_common(20)
    for id, score in top_20:
        print(f"{get_anime_title_by_id(db, id)}: {score}")

if __name__ == "__main__":
    recommend_for_user(1)