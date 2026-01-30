import httpx
import structlog
from app.schemas.task import WorkflowTaskUpdate
from app.core.config import settings

logger = structlog.get_logger()

class APIPublisher:
    def __init__(self):
        # The URL of your own API that handles task updates
        self.base_url = settings.WF_CALL_BACK_URL 
        self.timeout = httpx.Timeout(5.0)

    def send_callback(
        self,
        workflow_execution_id: str,
        workflow_task_id: str,
        payload: WorkflowTaskUpdate
    ) -> bool:
        """
        Invokes the PUT /workflows/executions/{id}/tasks/{id} endpoint
        to update the task status and output.
        """
        url = f"{self.base_url}/api/v1/workflows/executions/{workflow_execution_id}/tasks/{workflow_task_id}"
        
        log = logger.bind(
            execution_id=workflow_execution_id,
            task_id=workflow_task_id,
            new_status=payload.status
        )
        #Sync call, because this is already running within async process
        with httpx.Client(timeout=self.timeout) as client:
                log.info("sending_task_callback")
                
                response = client.put(url, json=payload.model_dump(), timeout=10.0)
                response.raise_for_status()
                return response.json()