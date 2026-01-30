import httpx
import structlog
from app.schemas.task import WorkflowTaskUpdate
from app.core.config import settings

logger = structlog.get_logger()

class APIPublisher:
    def __init__(self):
        # The URL of your own API that handles task updates
        self.base_url = settings.API_V1_STR 
        self.timeout = httpx.Timeout(5.0)

    async def send_callback(
        self,
        workflow_execution_id: str,
        workflow_task_id: str,
        payload: WorkflowTaskUpdate
    ) -> bool:
        """
        Invokes the PUT /workflows/executions/{id}/tasks/{id} endpoint
        to update the task status and output.
        """
        url = f"{self.base_url}/workflows/executions/{workflow_execution_id}/tasks/{workflow_task_id}"
        
        log = logger.bind(
            execution_id=workflow_execution_id,
            task_id=workflow_task_id,
            new_status=payload.workflow_status
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                log.info("sending_task_callback")
                
                # We use model_dump(mode="json") to ensure Enums and Dicts 
                # are serialized correctly for the wire
                response = await client.put(
                    url,
                    json=payload.model_dump(mode="json")
                )
                
                response.raise_for_status()
                log.info("callback_success")
                return True

            except httpx.HTTPStatusError as e:
                log.error("callback_http_error", status_code=e.response.status_code, detail=e.response.text)
                return False
            except Exception as e:
                log.error("callback_failed", error=str(e))
                return False