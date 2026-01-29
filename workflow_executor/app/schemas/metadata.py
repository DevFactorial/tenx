from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional
from workflow_defn import WorkflowInputDefn

class WorkflowMetadataBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    workflow_defn: WorkflowInputDefn = None
    run_schedule: Optional[str] = None

class WorkflowMetadataCreate(WorkflowMetadataBase):
    workflow_defn_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")

class WorkflowMetadataUpdate(WorkflowMetadataBase):
    name: Optional[str] = None
    description: Optional[str] = None
    run_schedule: Optional[str] = None

class WorkflowMetadataRead(WorkflowMetadataBase):
    workflow_defn_id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    class Config:
        from_attributes = True