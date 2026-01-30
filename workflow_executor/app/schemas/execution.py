from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime

class WorkflowExecutionCreate(BaseModel):
    workflow_defn_id: str
    workflow_input: dict[str, Any]

class WorkflowExecutionRead(BaseModel):
    workflow_execution_id: str
    workflow_status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    
    class Config:
        from_attributes = True