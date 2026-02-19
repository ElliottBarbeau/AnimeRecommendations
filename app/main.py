from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import SessionLocal
from app.api.v1.router import api_router

app = FastAPI(title="Anime recommendations engine")
app.include_router(api_router, prefix="/api/v1")