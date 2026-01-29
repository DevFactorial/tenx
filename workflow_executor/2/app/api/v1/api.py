from fastapi import APIRouter
from app.api.v1.endpoints import users, items, auth, analytics

api_router = APIRouter()

# Each module's router is "mounted" with a specific tag and prefix
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])