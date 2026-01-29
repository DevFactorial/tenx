from fastapi import APIRouter, Depends, status
from app.api import deps
from app.schemas.task import TaskExecutionCreate, TaskExecutionRead
from app.services.task_execution_service import task_execution_service

router = APIRouter()

@router.post(
    "/run", 
    response_model=TaskExecutionRead, 
    status_code=status.HTTP_201_CREATED,
    summary="Execute a workflow task"
)
async def run_task(
    payload: TaskExecutionCreate
):
    """
    Triggers the execution of a specific task within a workflow context.
    Creates a task execution record and initiates the task logic.
    """
    user_id = "worker_node_01" # In prod, this might be the ID of the worker
    return await task_execution_service.execute(
        payload=payload, user_id=user_id
    )