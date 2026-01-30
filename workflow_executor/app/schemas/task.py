from pydantic import BaseModel
from typing import Any, List
from app.models.workflow.status import WorkflowStatus
from app.schemas.workflow_defn import TaskDefn, TaskInputMapping
from datetime import datetime

class WorkflowTaskUpdate(BaseModel):
    workflow_status: WorkflowStatus  # Maps to workflow_task_status
    workflow_task_output: dict[str, Any] | None = None
    
class WorkflowTaskRead(BaseModel):
    workflow_task_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    
class TaskExecutionCreate(BaseModel):
    workflow_task_id: str
    workflow_defn_id: str
    workflow_execution_id: str
    workflow_task_input: List[TaskInputMapping]
    task_defn: TaskDefn