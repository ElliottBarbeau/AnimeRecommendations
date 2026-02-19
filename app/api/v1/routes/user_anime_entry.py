from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.deps import get_db
from app.db.models.user_anime_entry import UserAnimeEntry
from app.db.models.user import User
from app.schemas.user_anime_entry import UserAnimeEntryCreate, UserAnimeEntryRead

router = APIRouter(prefix="/entry", tags=["Entry"])

def _entry_read_with_user(entry: UserAnimeEntry, user: User) -> UserAnimeEntryRead:
    return UserAnimeEntryRead(
        id=entry.id,
        user_id=entry.user_id,
        provider=user.provider,
        provider_username=user.provider_username,
        anime_id=entry.anime_id,
        status=entry.status,
        score=entry.score,
        progress=entry.progress,
    )

@router.get("/by-id/{id}", response_model=UserAnimeEntryRead)
def get_entry(id: int, db: Session=Depends(get_db)):
    row = db.execute(
        select(UserAnimeEntry, User)
        .join(User, User.id == UserAnimeEntry.user_id)
        .where(UserAnimeEntry.id == id)
    ).one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry, user = row
    return _entry_read_with_user(entry, user)

@router.post("/", response_model=UserAnimeEntryRead)
def create_entry(payload: UserAnimeEntryCreate, db: Session=Depends(get_db)):
    existing = db.execute(
        select(UserAnimeEntry)
        .where(UserAnimeEntry.user_id == payload.user_id, UserAnimeEntry.anime_id == payload.anime_id)
        ).scalar_one_or_none()
    
    if existing:
        # eventually change this to update scores if the user has changed their entry since last list parse
        raise HTTPException(status_code=409, detail="User anime entry already exists")
    
    entry = UserAnimeEntry(**payload.model_dump())
    db.add(entry)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User anime entry already exists")

    row = db.execute(
        select(UserAnimeEntry, User)
        .join(User, User.id == UserAnimeEntry.user_id)
        .where(UserAnimeEntry.id == entry.id)
    ).one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found after create")

    created_entry, user = row
    return _entry_read_with_user(created_entry, user)
    


