from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.deps import get_db
from app.db.models.anime import Anime
from app.schemas.anime import AnimeRead, AnimeCreate

router = APIRouter(prefix="/anime", tags=["Anime"])

@router.get("/by-id/{id}", response_model=AnimeRead)
def get_anime(id: int, db: Session=Depends(get_db)):
    anime = db.execute(select(Anime).where(Anime.id == id)).scalar_one_or_none()
    if anime is None:
        raise HTTPException(status_code=404, detail="Anime not found")
    return anime

@router.post("/", response_model=AnimeRead)
def create_anime(payload: AnimeCreate, db: Session=Depends(get_db)):
    existing = db.execute(
        select(Anime)
        .where(Anime.provider == payload.provider, Anime.provider_anime_id == payload.provider_anime_id)
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=409, detail="Anime already exists")
    
    anime = Anime(**payload.model_dump())
    db.add(anime)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Anime already exists")

    db.refresh(anime)
    return anime
