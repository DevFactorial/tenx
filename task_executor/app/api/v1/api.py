from fastapi import APIRouter
from app.api.v1.endpoints import task

api_router = APIRouter()

# Each module's router is "mounted" with a specific tag and prefix
api_router.include_router(task.router, prefix="/task", tags=["users"])
