from pydantic import BaseModel
from typing import Any, List, Optional
from app.models.workflow.status import WorkflowStatus
from app.schemas.workflow_defn import TaskDefn, TaskInputMapping
from datetime import datetime
import enum

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    STARTED = "STARTED"
    

    
class WorkflowTaskRead(BaseModel):
    workflow_task_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    
class TaskExecutionCreate(TaskDefn):
    workflow_task_id: str
    workflow_defn_id: str
    workflow_execution_id: str
    workflow_task_input: List[TaskInputMapping]

    
class WorkflowTaskUpdate(BaseModel):
    status: TaskStatus  
    error: Optional[str] = None
    output: dict[str, Any] | None = None
    

class TaskExecutionResponse(BaseModel):
    workflow_task_id: str
    workflow_execution_id: str
    status: TaskStatus  
    error: Optional[str] = None
    
    class Config:
        from_attributes = True
        
class WorkflowTaskUpdateResponse(BaseModel):
    workflow_task_id: str

    