import httpx
import logging
from typing import Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from app.integrations.publisher import BasePublisher
from app.core.config import settings

logger = logging.getLogger(__name__)

class APIPublisher(BasePublisher):
    def __init__(self):
        self.worker_url = f"{settings.WORKER_BASE_URL}/v1/tasks/execute"
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    # Retry 3 times, waiting 2^x seconds between tries, 
    # only for connection errors or 5xx server errors.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError)),
        reraise=True # So the service layer knows it ultimately failed
    )
    async def publish(
        self, 
        execution_id: str, 
        task_id: str, 
        payload: Any
    ) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.worker_url,
                json={
                    "execution_id": execution_id,
                    "task_id": task_id,
                    "data": payload
                }
            )
            
            # If we get a 5xx, we want to retry. raise_for_status() 
            # helps tenacity catch it if we wrap it properly.
            if response.status_code >= 500:
                logger.warning(f"Worker node error {response.status_code}. Retrying...")
                response.raise_for_status() 
                
            return response.status_code == 200