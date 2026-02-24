from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.db.models.user import User
from app.services.recommend_for_user import recommend_for_user
from app.schemas.recommendations import RecommendationItem

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get("/", response_model=list[RecommendationItem])
def get_recommendations_for_user(user_id: int, db: Session=Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    items = recommend_for_user(db, user_id)
    if not items:
        return []
    return items
