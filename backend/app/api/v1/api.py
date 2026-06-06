from fastapi import APIRouter
from app.api.v1.endpoints import auth, complaints, suspects

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(complaints.router, prefix="/complaints", tags=["complaints"])
api_router.include_router(suspects.router, prefix="/suspects", tags=["suspects"])
