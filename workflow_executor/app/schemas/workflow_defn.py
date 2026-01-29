from enum import Enum
from typing import Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field, ConfigDict


class InputFetchSource(str, Enum):
    WORKFLOW_INPUT = "WORKFLOW_INPUT"
    TASK_OUTPUT = "TASK_OUTPUT"
    STATIC_VALUE = "STATIC_VALUE"


class WorkflowInputDefn(BaseModel):
    name: str
    description: str
    is_mandatory: bool = False
    default_value: Any = ""

class RuntimeType(str, Enum):
    PYTHON = "PYTHON"
    NODEJS = "NODEJS"
    BASH = "BASH"

class RuntimeConfig(BaseModel):
    runtime: RuntimeType = RuntimeType.PYTHON
    file_name: str = Field(..., description="The entry point file for the task logic")
    # TODO add memory_limit or cpu_limit here 


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


class TaskDefn(BaseTask):
    type: Literal["TASK"] = "TASK"
    runtime_config: RuntimeConfig
    input: List[TaskInputMapping] = Field(default_factory=list)
    output: List[TaskOutputDefn] = Field(default_factory=list)


class TaskGroupDefn(BaseTask):
    type: Literal["TASK_GROUP"] = "TASK_GROUP"
    # This allows for recursive task nesting
    tasks: List[Union["TaskDefn", "TaskGroupDefn"]] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    input: List[WorkflowInputDefn] = Field(default_factory=list)
    tasks: List[Union[TaskDefn, TaskGroupDefn]] = Field(default_factory=list)

# Crucial for Pydantic to resolve recursive references
TaskGroupDefn.model_rebuild()