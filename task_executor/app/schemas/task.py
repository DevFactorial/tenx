from pydantic import BaseModel
from typing import Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from app.schemas.status import TaskStatus


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

class TaskExecutionCreate(TaskDefn):
    workflow_task_id: str
    workflow_defn_id: str
    workflow_execution_id: str
    workflow_task_input: List[TaskInputMapping]
    
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
    status: TaskStatus  
    error: Optional[str] = None
    output: Optional[dict[str, Any]] | None = None
    

class TaskExecutionResponse(BaseModel):
    workflow_task_id: str
    workflow_execution_id: str
    status: TaskStatus  
    error: Optional[str] = None
    
    class Config:
        from_attributes = True