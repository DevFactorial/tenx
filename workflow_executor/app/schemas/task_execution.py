from pydantic import BaseModel, ConfigDict
from typing import Any, Optional, List, Dict
from app.models.workflow.status import WorkflowStatus
from app.schemas.workflow_defn import TaskInputMapping, TaskOutputDefn

class WorkflowTaskExecutionRead(BaseModel):
    workflow_execution_id: str
    workflow_task_id: str
    task_name: str
    workflow_defn_id: str
    workflow_status: WorkflowStatus
    workflow_task_input: List[TaskInputMapping]
    #workflow_task_output: Optional[List[TaskOutputDefn]] = None
    workflow_task_output: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)