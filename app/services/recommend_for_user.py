from app.db.session import SessionLocal
from app.db.repositories.user_anime_entries import get_entries_above_score

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

    # after this works, add similarity weighing

    # steps:

    # get list of shows for the user that are scored >= 8.0

    db = SessionLocal()
    try:
        candidate_shows = get_entries_above_score(db, user_id, 8)
    finally:
        db.close()

    print(candidate_shows)

if __name__ == "__main__":
    recommend_for_user(1)