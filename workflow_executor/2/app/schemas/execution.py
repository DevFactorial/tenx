from pydantic import BaseModel, Field
from typing import Any

class WorkflowExecutionCreate(BaseModel):
    workflow_defn_id: str
    workflow_input: dict[str, Any]

class WorkflowExecutionRead(BaseModel):
    workflow_execution_id: str
    workflow_status: str
    
    class Config:
        from_attributes = True