
from app.schemas.task import TaskExecutionCreate, TaskExecutionAccepted
from app.schemas.task import WorkflowTaskUpdate
from app.schemas.status import WorkflowStatus
from app.services.task_runtime_service import TaskRuntimeService
from app.integrations.api_publisher import APIPublisher

class TaskExecutionService:
    async def execute(
        self,  payload: TaskExecutionCreate, user_id: str,
        task_runtime_service: TaskRuntimeService,
        publisher: APIPublisher,
    ) -> TaskExecutionAccepted:
       runtime_config = payload.task_defn.runtime_config 
        
       # 2. Invoke the runtime async
       try:
            # We don't 'await' here if you want it truly backgrounded, 
            # OR we await here if this service IS the worker.
            task_runtime_service.run_task_logic(
                runtime_config=runtime_config,
                payload= payload,
                publisher=publisher
            )
            
           
            
       except Exception as e:
            # 4. Handle failure
            pass
            
       return TaskExecutionAccepted(workflow_execution_id = payload.workflow_execution_id, 
                                         workflow_task_id = payload.workflow_task_id)
       
        
      
        
        

task_execution_service = TaskExecutionService()