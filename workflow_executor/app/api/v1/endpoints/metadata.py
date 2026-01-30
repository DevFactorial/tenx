from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import deps
from app.schemas.metadata import (
    WorkflowMetadataCreate,
    WorkflowMetadataRead,
    WorkflowMetadataUpdate
)
from app.services.workflow_metadata_service import WorkflowMetadataService

router = APIRouter()

@router.post(
    "/", 
    response_model=WorkflowMetadataRead, 
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow definition"
)
async def create_metadata(
    payload: WorkflowMetadataCreate, 
    db: AsyncSession = Depends(deps.get_db),
    metadata_service: WorkflowMetadataService = Depends(deps.get_metadata_service)
):
    """
    Register a new workflow definition in the system.
    """
    existing = await metadata_service.get_by_name(db, name=payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A workflow with this ID already exists."
        )
    return await metadata_service.create(db, obj_in=payload, user_id="admin_user")


@router.get(
    "/", 
    response_model=list[WorkflowMetadataRead],
    summary="List workflow definitions"
)
async def list_metadata(
    name: Optional[str] = Query(None, description="Filter by workflow name (partial match)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(deps.get_db),
    metadata_service: WorkflowMetadataService = Depends(deps.get_metadata_service)
):
    """
    Retrieve workflow definitions with optional name filtering and pagination.
    """
    return await metadata_service.get_multi(
        db, skip=skip, limit=limit, name=name
    )


@router.get(
    "/{workflow_defn_id}", 
    response_model=WorkflowMetadataRead,
    summary="Get workflow by ID"
)
async def get_metadata(
    workflow_defn_id: str, 
    db: AsyncSession = Depends(deps.get_db),
    metadata_service: WorkflowMetadataService = Depends(deps.get_metadata_service)
):
    """
    Fetch a single workflow definition by its unique identifier.
    """
    wf = await metadata_service.get(db, workflow_defn_id=workflow_defn_id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Workflow definition not found."
        )
    return wf


@router.put(
    "/{workflow_defn_id}", 
    response_model=WorkflowMetadataRead,
    summary="Update workflow definition"
)
async def update_metadata(
    workflow_defn_id: str, 
    payload: WorkflowMetadataUpdate, 
    db: AsyncSession = Depends(deps.get_db),
    metadata_service: WorkflowMetadataService = Depends(deps.get_metadata_service)
):
    """
    Update an existing workflow definition. Only provided fields will be modified.
    """
    updated_wf = await metadata_service.update(
        db, 
        workflow_defn_id=workflow_defn_id, 
        obj_in=payload, 
        user_id="admin_user"
    )
    if not updated_wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Workflow definition not found."
        )
    return updated_wf


@router.delete(
    "/{workflow_defn_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow definition"
)
async def delete_metadata(
    workflow_defn_id: str, 
    db: AsyncSession = Depends(deps.get_db),
    metadata_service: WorkflowMetadataService = Depends(deps.get_metadata_service)
):
    """
    Remove a workflow definition. This will fail if there are active executions 
    depending on this metadata (unless cascade is configured).
    """
    deleted_wf = await metadata_service.delete(db, workflow_defn_id=workflow_defn_id)
    if not deleted_wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Workflow definition not found."
        )
    return None