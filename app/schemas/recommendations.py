from pydantic import BaseModel

class RecommendationItem(BaseModel):
    title: str
    score: float