import asyncio
import os
import structlog
from app.schemas.task import RuntimeType
from app.schemas.task import TaskExecutionCreate, WorkflowTaskUpdate
from app.schemas.status import TaskStatus
from app.integrations.api_publisher import APIPublisher
from app.services.worker import execute_python_script

logger = structlog.get_logger()

class TaskRuntimeService:
    async def run_task_logic(self, payload: TaskExecutionCreate, publisher):
        task_input = payload.workflow_task_input
        runtime = payload.runtime_config.runtime
        file_name = payload.runtime_config.file_name

        if runtime == RuntimeType.PYTHON:
            return await self._execute_python(file_name, task_input, payload.workflow_execution_id, payload.workflow_task_id)
        
        logger.error("unsupported_runtime", runtime=runtime)
        raise ValueError(f"Runtime {runtime} not supported.")

    async def _execute_python(self, file_name: str, task_input: dict, execution_id: str, task_id: str):
        """
        Executes a python file as a separate async process.
        """
        if not os.path.exists(file_name):
            logger.error("file_not_found", file=file_name)
            raise FileNotFoundError(f"Script {file_name} not found.")

        logger.info("executing_python_script", file=file_name)
        # If task_input is a list of Pydantic models, convert them to JSON-safe dicts
        serializable_input = [
            item.model_dump(mode='json') if hasattr(item, 'model_dump') else item 
            for item in task_input
        ]

        # .delay() sends the task to the queue and returns immediately
        task = execute_python_script.delay(file_name, serializable_input, execution_id, task_id)
        return {"task_id": task.id}
        
    

task_runtime_service = TaskRuntimeService()