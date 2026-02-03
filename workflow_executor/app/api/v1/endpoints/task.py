from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import deps
from app.services.workflow_service import WorkflowExecutionService
from app.schemas.task import WorkflowTaskUpdate, WorkflowTaskUpdateResponse
from app.services.workflow_metadata_service import WorkflowMetadataService
from app.models.workflow.task import WorkflowTaskExecution # The Model
from app.schemas.task_execution import WorkflowTaskExecutionRead   # The Schema
from fastapi import Query
from typing import List

router = APIRouter()

@router.put(
    "/executions/{workflow_execution_id}/tasks/{workflow_task_id}",
    response_model=WorkflowTaskUpdateResponse
)
async def update_workflow_task(
    workflow_execution_id: str,
    workflow_task_id: str,
    payload: WorkflowTaskUpdate,
    db: AsyncSession = Depends(deps.get_db),
    meta_service: WorkflowMetadataService = Depends(deps.get_metadata_service),
    publisher = Depends(deps.get_publisher),
    workflow_execution_service: WorkflowExecutionService = Depends(deps.get_execution_service),
):
    """
    Update the status and output of a specific task within a workflow execution.
    """
    user_id = "system_user" # In production, get from deps.get_current_user
    
    response = await workflow_execution_service.update_task(
        db,
        metadata_service=meta_service,
        publisher=publisher,
        execution_id=workflow_execution_id,
        task_id=workflow_task_id,
        payload=payload,
        user_id=user_id
    )
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {workflow_task_id} not found for execution {workflow_execution_id}"
        )
        
    return response

@router.get(
    "/executions/{workflow_execution_id}/tasks/{workflow_task_id}", 
    response_model=WorkflowTaskExecutionRead
)
async def get_task_execution(
    workflow_execution_id: str,
    workflow_task_id: str,
    db: AsyncSession = Depends(deps.get_db),
    workflow_execution_service: WorkflowExecutionService = Depends(deps.get_execution_service),
):
    """
    Fetch a specific task execution by its composite primary key.
    """
    
    
    task_exec = await workflow_execution_service.get_task_execution(
        db=db, 
        execution_id=workflow_execution_id, 
        task_id=workflow_task_id
    )

    if not task_exec:
        raise HTTPException(
            status_code=404, 
            detail=f"Task {workflow_task_id} not found for execution {workflow_execution_id}"
        )

    return task_exec

@router.get(
    "/executions/{workflow_execution_id}/tasks", 
    response_model=List[WorkflowTaskExecutionRead]
)
async def list_tasks(
    workflow_execution_id: str,
    limit: int = Query(default=100, le=500), # Max 500 per request
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(deps.get_db),
    workflow_execution_service: WorkflowExecutionService = Depends(deps.get_execution_service),
):
    """
    Returns all tasks associated with a specific workflow execution.
    """
    tasks = await workflow_execution_service.list_task_executions(
        db=db, 
        execution_id=workflow_execution_id, 
        limit=limit, 
        offset=offset
    )
    
    return tasks