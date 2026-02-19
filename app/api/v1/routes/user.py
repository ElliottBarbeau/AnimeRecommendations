from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db
from app.db.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users")

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
    db.commit()
    db.refresh(user)
    return user
