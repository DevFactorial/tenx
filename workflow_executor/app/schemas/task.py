from pydantic import BaseModel
from typing import Any
from app.models.workflow.status import WorkflowStatus
from app.schemas.workflow_defn import TaskDefn

class WorkflowTaskUpdate(BaseModel):
    workflow_status: WorkflowStatus  # Maps to workflow_task_status
    workflow_task_output: dict[str, Any] | None = None
    
    
class TaskExecutionCreate(BaseModel):
    workflow_task_id: str
    workflow_defn_id: str
    workflow_execution_id: str
    workflow_task_input: dict[str, Any]
    task_defn: TaskDefn