from fastapi import APIRouter, Depends, status
from app.core import deps
from app.schemas.task import TaskExecutionCreate, TaskExecutionRead, TaskExecutionResponse
from app.services.task_execution_service import TaskExecutionService
from app.services.task_runtime_service import TaskRuntimeService

router = APIRouter()

@router.post(
    "/run", 
    response_model=TaskExecutionResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Execute a workflow task"
)
async def run_task(
    payload: TaskExecutionCreate,
    publisher = Depends(deps.get_publisher),
    task_execution_service: TaskExecutionService = Depends(deps.get_task_execution_service),
    task_runtime_service: TaskRuntimeService = Depends(deps.get_task_runtime_service),
) -> TaskExecutionResponse:
    """
    Triggers the execution of a specific task within a workflow context.
    Creates a task execution record and initiates the task logic.
    """
    user_id = "worker_node_01" # In prod, this might be the ID of the worker
    return await task_execution_service.execute(
        payload=payload, user_id=user_id,
        task_runtime_service= task_runtime_service,
        publisher=publisher
    )