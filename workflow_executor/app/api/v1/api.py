from fastapi import APIRouter
from app.api.v1.endpoints import execution, metadata, task

api_router = APIRouter()

# Each module's router is "mounted" with a specific tag and prefix
api_router.include_router(execution.router, prefix="/workflows", tags=["execution"])
api_router.include_router(metadata.router, prefix="/workflows", tags=["metadata"])
api_router.include_router(task.router, prefix="/workflows", tags=["task"])