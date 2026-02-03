from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional
from datetime import datetime 

class WorkflowExecutionCreate(BaseModel):
    workflow_defn_id: str
    workflow_input: dict[str, Any]

class WorkflowExecutionRead(BaseModel):
    workflow_execution_id: str
    workflow_status: str
    workflow_input: dict[str, Any]
    workflow_output: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    
    model_config = ConfigDict(from_attributes=True)