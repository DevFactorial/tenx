from typing import AsyncGenerator
from app.core.config import settings
from app.integrations.publisher import BasePublisher
from app.integrations.api_publisher import APIPublisher
from app.services.task_execution_service import TaskExecutionService
from app.services.task_runtime_service import TaskRuntimeService

# --- Service Dependencies ---
# These return new instances of services for each request
def get_task_execution_service() -> TaskExecutionService:
    return TaskExecutionService()

def get_task_runtime_service() -> TaskRuntimeService:
    return TaskRuntimeService()


def get_publisher() -> BasePublisher:
    # Factory method to return publisher
    return APIPublisher()