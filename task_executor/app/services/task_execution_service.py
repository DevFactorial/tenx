
from app.schemas.task import TaskExecutionCreate
from app.schemas.workflow import WorkflowTaskUpdate
from app.models.status import WorkflowStatus

class TaskExecutionService:
    async def execute(
        self,  payload: TaskExecutionCreate, user_id: str
    ):
       runtime_config = payload.runtime_config 
        
       # 2. Invoke the runtime async
       try:
            # We don't 'await' here if you want it truly backgrounded, 
            # OR we await here if this service IS the worker.
            result = await task_runtime_service.run_task_logic(
                runtime_config=runtime_config,
                payload= payload
            )
            # 3. Update task status to COMPLETED
            await self._update_task_status(db, payload.task_id, "COMPLETED", result)
            
       except Exception as e:
            # 4. Handle failure
            await self._update_task_status(db, payload.task_id, "FAILED", str(e))
       
        
      
        
        

task_execution_service = TaskExecutionService()