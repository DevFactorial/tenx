import asyncio
import os
import structlog
from app.schemas.workflow_defn import RuntimeType
from app.schemas.task import TaskExecutionCreate, WorkflowTaskUpdate
from app.models.status import WorkflowStatus
from app.integrations.api_publisher import APICallback

logger = structlog.get_logger()

class TaskRuntimeService:
    async def run_task_logic(self, payload: TaskExecutionCreate):
        task_input = payload.workflow_task_input
        runtime = payload.task_defn.runtime_config.get("runtime")
        file_name = payload.task_defn.runtime_config.get("file_name")

        if runtime == RuntimeType.PYTHON:
            return await self._execute_python(file_name, task_input)
        
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

        # In production, you'd pass input as CLI args or environment variables
        process = await asyncio.create_subprocess_exec(
            "python3", file_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info("python_script_success", file=file_name)
            result = stdout.decode().strip()
            self.finish_task(execution_id, task_id,result, True)
            return result
        else:
            error_msg = stderr.decode().strip()
            logger.error("python_script_failed", file=file_name, error=error_msg)
            self.finish_task(execution_id, task_id,result, False)
            raise RuntimeError(f"Script failed with exit code {process.returncode}: {error_msg}")
        
        
    async def finish_task(self, execution_id: str, task_id: str, result: str, success: bool):
        callback_client = APICallback()
    
        # Construct the update payload
        status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
        update_payload = WorkflowTaskUpdate(
            workflow_status=status,
            workflow_task_output={"result": result}
        )
    
        # Invoke the API
        await callback_client.send_callback(
            workflow_execution_id=execution_id,
            workflow_task_id=task_id,
            payload=update_payload
        )

task_runtime_service = TaskRuntimeService()