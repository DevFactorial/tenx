from pydantic import BaseModel
from typing import Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from app.schemas.status import WorkflowStatus


class InputFetchSource(str, Enum):
    WORKFLOW_INPUT = "WORKFLOW_INPUT"
    TASK_OUTPUT = "TASK_OUTPUT"
    STATIC_VALUE = "STATIC_VALUE"

class TaskInputMapping(BaseModel):
    name: str
    description: str
    fetch_from: InputFetchSource = InputFetchSource.WORKFLOW_INPUT
    fetch_key: Optional[str] = None
    value: Optional[Any] = None


class TaskOutputDefn(BaseModel):
    name: str
    description: str


class BaseTask(BaseModel):
    name: str
    description: str
    id: str
    run_after: List[str] = Field(default_factory=list)

class RuntimeType(str, Enum):
    PYTHON = "PYTHON"
    NODEJS = "NODEJS"
    BASH = "BASH"

class RuntimeConfig(BaseModel):
    runtime: RuntimeType = RuntimeType.PYTHON
    file_name: str = Field(..., description="The entry point file for the task logic")
    # TODO add memory_limit or cpu_limit here 

class TaskDefn(BaseTask):
    type: Literal["TASK"] = "TASK"
    runtime_config: RuntimeConfig
    input: List[TaskInputMapping] = Field(default_factory=list)
    output: List[TaskOutputDefn] = Field(default_factory=list)

class TaskExecutionCreate(BaseModel):
    workflow_task_id: str
    workflow_defn_id: str
    workflow_execution_id: str
    workflow_task_input: dict[str, Any]
    task_defn: TaskDefn
    
class RuntimeType(str, Enum):
    PYTHON = "PYTHON"
    NODEJS = "NODEJS"
    BASH = "BASH"

class TaskExecutionRead(TaskExecutionCreate):
    workflow_status: str
    workflow_task_type: str
    created_at: Any
    task_defn: TaskDefn
    
    class Config:
        from_attributes = True
        
class WorkflowTaskUpdate(BaseModel):
    workflow_status: WorkflowStatus  # Maps to workflow_task_status
    workflow_task_output: dict[str, Any] | None = None
    

class TaskExecutionAccepted(BaseModel):
    workflow_task_id: str
    workflow_execution_id: str
    
    class Config:
        from_attributes = True