from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import deps
from app.services.workflow_service import WorkflowExecutionService
from app.schemas.task import WorkflowTaskUpdate, WorkflowTaskUpdateResponse
from app.services.workflow_metadata_service import WorkflowMetadataService

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
    workflow_execution_service: WorkflowExecutionService = Depends(deps.get_execution_service),
):
    """
    Update the status and output of a specific task within a workflow execution.
    """
    user_id = "system_user" # In production, get from deps.get_current_user
    
    response = await workflow_execution_service.update_task(
        db,
        metadata_service=meta_service,
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