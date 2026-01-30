from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from structlog import get_logger
from fastapi import Request
import uuid
import structlog

logger = get_logger()

def get_application() -> FastAPI:
    _app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Set all CORS enabled origins
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API Routers
    _app.include_router(api_router, prefix=settings.API_V1_STR)

    return _app

app = get_application()

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": settings.VERSION}

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # CRITICAL: Clear context from previous requests on this thread/worker
    structlog.contextvars.clear_contextvars()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    structlog.contextvars.bind_contextvars(request_id=request_id)

    logger.info("request_started", path=request.url.path, method=request.method)
    
    response = await call_next(request)
    
    logger.info("request_finished", status_code=response.status_code)
    return response
