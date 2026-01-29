from pydantic import BaseModel
from typing import Any
from app.models.workflow.status import WorkflowStatus

class WorkflowTaskUpdate(BaseModel):
    workflow_status: WorkflowStatus  # Maps to workflow_task_status
    workflow_task_output: dict[str, Any] | None = None