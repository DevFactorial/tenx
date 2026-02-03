from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import deps
from app.schemas.execution import WorkflowExecutionCreate, WorkflowExecutionRead
from app.services.workflow_service import WorkflowExecutionService
from app.services.workflow_metadata_service import WorkflowMetadataService

router = APIRouter()

@router.post(
    "/executions", 
    response_model=WorkflowExecutionRead, 
    status_code=status.HTTP_201_CREATED
)
async def execute_workflow(
    payload: WorkflowExecutionCreate,
    db: AsyncSession = Depends(deps.get_db),
    publisher = Depends(deps.get_publisher),
    workflow_execution_service: WorkflowExecutionService = Depends(deps.get_execution_service),
    meta_service: WorkflowMetadataService = Depends(deps.get_metadata_service)
    # current_user = Depends(deps.get_current_user) # Logic for 'created_by'
):
    """
    Triggers the execution of a predefined workflow.
    """
    user_id = "system_user" # Replace with current_user.id in real app
    return await workflow_execution_service.execute(
        db, 
        metadata_service=meta_service,
        publisher=publisher,
        payload=payload, 
        user_id=user_id
    )
    
@router.get(
    "/executions/{workflow_execution_id}", 
    response_model=WorkflowExecutionRead
)
async def get_workflow_execution(
    workflow_execution_id: str,
     db: AsyncSession = Depends(deps.get_db),
     workflow_execution_service: WorkflowExecutionService = Depends(deps.get_execution_service),
):
    """
    Get full details of a specific workflow execution.
    """
    execution = await workflow_execution_service.get_execution_by_id(
        db=db, 
        execution_id=workflow_execution_id
    )

    if not execution:
        raise HTTPException(
            status_code=404, 
            detail=f"Workflow execution {workflow_execution_id} not found"
        )

    return execution