from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.services.workflow_metadata_service import WorkflowMetadataService
from app.services.workflow_service import WorkflowExecutionService
from app.integrations.publisher import BasePublisher
from app.integrations.api_publisher import APIPublisher

engine = create_async_engine(
    str(settings.sqlalchemy_database_uri),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

async_session_local = async_sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_local() as session:
        yield session
        
# --- Service Dependencies ---
# These return new instances of services for each request
def get_metadata_service() -> WorkflowMetadataService:
    return WorkflowMetadataService()

def get_execution_service() -> WorkflowExecutionService:
    return WorkflowExecutionService()

def get_publisher() -> BasePublisher:
    # Factory method to return publisher
    return APIPublisher()