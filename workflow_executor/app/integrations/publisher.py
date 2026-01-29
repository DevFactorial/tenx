from abc import ABC, abstractmethod
from typing import Any

class BasePublisher(ABC):
    @abstractmethod
    async def publish(
        self,
        payload: Any
    ) -> bool:
        """
        Contract for publishing a task to a worker.
        Returns True if successful.
        """
        pass