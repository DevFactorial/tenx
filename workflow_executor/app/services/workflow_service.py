import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import WorkflowExecution, WorkflowStatus
from app.schemas.execution import WorkflowExecutionCreate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import WorkflowTaskExecution, WorkflowExecution
from app.schemas.execution import WorkflowTaskUpdate
from sqlalchemy import func
from app.models.workflow.status import WorkflowStatus
from app.services.workflow_metadata_service import WorkflowMetadataService
from app.integrations.publisher import BasePublisher
from structlog import get_logger
from app.schemas.task import TaskExecutionCreate
from fastapi import HTTPException, status

logger = get_logger()

# State Machine Configuration
VALID_TRANSITIONS = {
    WorkflowStatus.PENDING: [WorkflowStatus.RUNNING, WorkflowStatus.FAILED],
    WorkflowStatus.RUNNING: [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED],
    WorkflowStatus.COMPLETED: [],  # Terminal state: no further changes allowed
    WorkflowStatus.FAILED: [WorkflowStatus.PENDING], # Only allowed if retrying
}


class WorkflowExecutionService:
    def __init__(self):
        pass
    
    async def execute(self, 
                      db: AsyncSession, 
                      metadata_service: WorkflowMetadataService, # Injected
                      publisher: BasePublisher, # Injected interface
                      payload: WorkflowExecutionCreate, 
                      user_id: str):
        # Bind context so all subsequent logs in this method carry these IDs
        structlog.contextvars.bind_contextvars(
            workflow_defn_id=payload.workflow_defn_id,
            user_id=user_id
        )
        log = logger.bind(
            workflow_defn_id=payload.workflow_defn_id,
            user_id=user_id
        )
        log.info("workflow_execution_init")
        wf_exec = None
        try:
            # 1. Fetch Workflow Definition
            metadata = await metadata_service.get(db, payload.workflow_defn_id)
            if not metadata:
                raise ValueError(f"Workflow definition {payload.workflow_defn_id} not found")
            
            # 2. Create Workflow Execution Record
            execution_id = f"wf_exec_{uuid.uuid4().hex[:12]}"
            structlog.contextvars.bind_contextvars(
                execution_id=execution_id
            ) 
            wf_exec = WorkflowExecution(
                workflow_execution_id=execution_id,
                workflow_defn_id=payload.workflow_defn_id,
                workflow_input=payload.workflow_input,
                workflow_status=WorkflowStatus.RUNNING,
                created_by=user_id,
                updated_by=user_id
            )
            db.add(wf_exec)
            
            # 3. Handle First Task/Group in definition
            tasks_list = metadata.workflow_defn.get("tasks", [])
            log.info("workflow_execution_success", task_count=len(tasks_list))
            if not tasks_list:
                raise ValueError("Workflow definition has no tasks")
                
            first_item = tasks_list[0]
            
            # Determine if it's a single Task or a Task Group
            if first_item.get("type") == "TASK":
                await self.execute_task(db, publisher, execution_id, metadata.workflow_defn_id, first_item, user_id)
            
            elif first_item.get("type") == "TASK_GROUP":
                group_tasks = first_item.get("tasks", [])
                for task_in_group in group_tasks:
                    # Assuming group members are of type TASK
                    await self.execute_task(db, execution_id, metadata.workflow_defn_id, task_in_group, user_id)

            await db.commit()
            await db.refresh(wf_exec)
        except Exception as e:
            log.error("workflow_execution_failed", error=str(e), exc_info=True)
            raise
        return wf_exec

    async def execute_task(
        self, 
        db: AsyncSession, 
        publisher: BasePublisher, # Injected interface
        execution_id: str, 
        defn_id: str, 
        task_data: dict, 
        user_id: str
    ):
        """
        Handles the lifecycle of a single task execution record and worker notification.
        """
        task_id = task_data.get("id")
        structlog.contextvars.bind_contextvars(
                task_id=task_id
        ) 
        logger.info("executing task")
        
        # 1. Create record with PENDING status
        task_exec = WorkflowTaskExecution(
            workflow_execution_id=execution_id,
            workflow_task_id=task_id,
            workflow_defn_id=defn_id,
            task_name = task_data.get("task_name"),
            workflow_task_type=task_data.get("type", "TASK"),
            workflow_status=WorkflowStatus.PENDING,
            workflow_task_input=task_data.get("input", []),
            created_by=user_id,
            updated_by=user_id
        )
        db.add(task_exec)
        await db.flush() # Flush so the record exists for the publisher if needed

        # 2. Invoke Publisher
        # We pass the metadata so the worker knows what to run
        try:
            task_exec_create = TaskExecutionCreate(task_id,
                                    defn_id,
                                    execution_id,
                                    task_data.get("input", []),
                                    task_data)
            await publisher.publish(
                task_exec_create
            )
            task_exec.workflow_status = WorkflowStatus.RUNNING
        except Exception as e:
            logger.error(f"Critical failure publishing task {task_id}: {str(e)}")
            task_exec.workflow_status = WorkflowStatus.FAILED
            # Optional: update parent workflow_execution to FAILED here as well

        # 3. Update status to RUNNING (IN PROGRESS)
        task_exec.workflow_status = WorkflowStatus.RUNNING
        task_exec.updated_by = user_id
        # No commit here; commit happens in the parent execute() to ensure atomicity
    
    async def update_task(
            self, 
            db: AsyncSession, 
            metadata_service: WorkflowMetadataService,
            execution_id: str, 
            task_id: str, 
            payload: WorkflowTaskUpdate,
            user_id: str
        ) -> WorkflowTaskExecution | None:
            # 1. Fetch current record to check current state
            result = await db.execute(
                select(WorkflowTaskExecution).where(
                    WorkflowTaskExecution.workflow_execution_id == execution_id,
                    WorkflowTaskExecution.workflow_task_id == task_id
                ).with_for_update() # Lock the row to prevent race conditions
             )
            task = result.scalars().first()
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
                
            # 2. State Machine Validation
            current_status = task.workflow_status
            new_status = payload.workflow_status

            if current_status != new_status:  # Only validate if status is changing
                allowed_statuses = VALID_TRANSITIONS.get(current_status, [])
                if new_status not in allowed_statuses:
                    raise HTTPException(
                        status_code = status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid transition: {current_status} -> {new_status}"
                    )
            # 3. Update the specific task
            task.workflow_status = new_status
            if payload.workflow_task_output is not None:
                task.workflow_task_output = payload.workflow_task_output
            task.updated_by = user_id
            # updated_at is handled by SQLAlchemy onupdate=func.now()
            query = (
                update(WorkflowTaskExecution)
                .where(
                    WorkflowTaskExecution.workflow_execution_id == execution_id,
                    WorkflowTaskExecution.workflow_task_id == task_id
                )
                .values(
                    workflow_status=payload.workflow_status,
                    workflow_task_output=payload.workflow_task_output,
                    updated_by=user_id,
                    updated_at=func.now()
                )
                .returning(WorkflowTaskExecution)
            )
            
            result = await db.execute(query)
            updated_task = result.scalars().first()
            
            if not updated_task:
                return None

            # 2. Production Logic: If task is completed, you might want to 
            # check if the whole workflow should transition status.
            # await self._refresh_workflow_status(db, execution_id)
            
            await db.commit()
            return updated_task
        
    async def _trigger_next_tasks(
        self, 
        db: AsyncSession, 
        metadata_service: WorkflowMetadataService,
        execution_id: str, 
        completed_task_id: str,
        defn_id: str,
        user_id: str
    ):
        # Fetch the full definition to find dependencies
        metadata = await metadata_service.get(db, defn_id)
        wf_defn = metadata.workflow_defn
        
        # Scan all tasks in the definition
        all_tasks = wf_defn.get("tasks", [])
        
        for item in all_tasks:
            # Handle Single Task or Task Group
            if item.get("type") == "TASK":
                await self._evaluate_and_run(db, execution_id, defn_id, item, completed_task_id, user_id)
            
            elif item.get("type") == "TASK_GROUP":
                # For groups, we check if the group itself is triggered, 
                # then run all tasks inside it
                if completed_task_id in item.get("run_after", []):
                    for sub_task in item.get("tasks", []):
                        await self.execute_task(db, execution_id, defn_id, sub_task, user_id)

    async def _evaluate_and_run(self, db, execution_id, defn_id, task_data, completed_id, user_id):
        """Checks if a task should run based on the task that just finished."""
        run_after = task_data.get("run_after", [])
        
        if completed_id in run_after:
            # Production Logic: In a real DAG, you'd check if ALL dependencies 
            # in 'run_after' are COMPLETED before starting this one.
            # For now, we trigger if the direct parent is done.
            await self.execute_task(db, execution_id, defn_id, task_data, user_id)

workflow_execution_service = WorkflowExecutionService()