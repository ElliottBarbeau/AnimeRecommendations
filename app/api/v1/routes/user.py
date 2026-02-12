from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db
from app.db.models.user import User
from app.schemas.user import UserCreate

router = APIRouter(prefix="/users")

@router.get("/by-id/{id}")
def get_user(id: int, db: Session=Depends(get_db)):
    user = db.execute(select(User).where(User.id == id)).scalar_one_or_none()
    return {"id": user.id, "public_id": user.public_id, "provider": user.provider, "provider_username": user.provider_username}

@router.post("/")
def create_user(payload: UserCreate, db: Session=Depends(get_db)):
    existing = db.execute(
        select(User).where(User.provider == payload.provider, User.provider_username == payload.provider_username)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user