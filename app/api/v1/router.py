from fastapi import APIRouter

from app.api.v1.routes.user import router as user_router
from app.api.v1.routes.anime import router as anime_router
from app.api.v1.routes.user_anime_entry import router as user_anime_entry_router
from app.api.v1.routes.recommendations import router as recommendations_router

api_router = APIRouter()
api_router.include_router(user_router)
api_router.include_router(anime_router)
api_router.include_router(user_anime_entry_router)