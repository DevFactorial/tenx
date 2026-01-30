
from app.schemas.task import TaskExecutionCreate, TaskExecutionResponse
from app.schemas.task import WorkflowTaskUpdate
from app.schemas.status import TaskStatus
from app.services.task_runtime_service import TaskRuntimeService
from app.integrations.api_publisher import APIPublisher
from fastapi import HTTPException, status

import structlog

logger = structlog.get_logger()

class TaskExecutionService:
    async def execute(
        self,  payload: TaskExecutionCreate, user_id: str,
        task_runtime_service: TaskRuntimeService,
        publisher: APIPublisher,
    ) -> TaskExecutionResponse:
       
       log = logger.bind(
            workflow_execution_id = payload.workflow_execution_id, 
            workflow_task_id = payload.workflow_task_id
        )
        
       # 2. Invoke the runtime async
       try:
            # We don't 'await' here if you want it truly backgrounded, 
            # OR we await here if this service IS the worker.
            log.info("Starting task run")
            task_result  = await task_runtime_service.run_task_logic(
                payload= payload,
                publisher=publisher
            )
            log.info("Initiated task run")
            
            return TaskExecutionResponse(workflow_execution_id = payload.workflow_execution_id, 
                                         workflow_task_id = payload.workflow_task_id,
                                         status = TaskStatus.STARTED)
            
       except Exception as e:
            log.error("Exception running task", error=str(e), exc_info=True)
            # 4. Handle failure
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
       
       
        
      
        
        

task_execution_service = TaskExecutionService()