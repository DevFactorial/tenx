import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import WorkflowExecution
from app.models.workflow.status import WorkflowStatus 
from app.schemas.execution import WorkflowExecutionCreate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import WorkflowTaskExecution, WorkflowExecution
from app.schemas.task import WorkflowTaskUpdate
from sqlalchemy import func
from app.models.workflow.status import WorkflowStatus
from app.services.workflow_metadata_service import WorkflowMetadataService
from app.integrations.publisher import BasePublisher
from structlog import get_logger
from app.schemas.task import TaskExecutionCreate, WorkflowTaskUpdateResponse
from fastapi import HTTPException, status
import structlog
from typing import List, Sequence
from typing import Any, List, Dict, Optional
from app.services.workflow_helper import resolve_task_inputs, find_next_tasks, WorkflowDependencyError

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
        logger.info(f"executing task for task_id {task_id}")
        
        # 1. Create record with PENDING status
        task_exec = WorkflowTaskExecution(
            workflow_execution_id=execution_id,
            workflow_task_id=task_id,
            workflow_defn_id=defn_id,
            task_name = task_data.get("name"),
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
            execution_data = {
                "workflow_task_id": task_id,
                "workflow_defn_id": defn_id,
                "workflow_execution_id": execution_id,
                "workflow_task_input": task_data.get("input", [])
            }
            merged_data = {**task_data, **execution_data}

            task_obj = TaskExecutionCreate(**merged_data)

            # 3. NOW you can call model_dump on task_obj
            # (NOT on merged_data)
            payload = task_obj.model_dump(mode='json')
            await publisher.publish(
                task_id=task_id,
                execution_id=execution_id,
                payload=payload
            )
            task_exec.workflow_status = WorkflowStatus.RUNNING
        except Exception as e:
            logger.error(f"Critical failure publishing task {task_id}: {str(e)}")
            task_exec.workflow_status = WorkflowStatus.FAILED
            # update parent workflow_execution to FAILED here as well
            await db.execute(
                update(WorkflowExecution)
                .where(WorkflowExecution.workflow_execution_id == execution_id)
                .values(workflow_status=WorkflowStatus.FAILED, updated_by=user_id)
            )

        task_exec.updated_by = user_id
        # No commit here; commit happens in the parent execute() to ensure atomicity
    
    async def update_task(
            self, 
            db: AsyncSession, 
            metadata_service: WorkflowMetadataService,
            publisher: BasePublisher, # Injected interface
            execution_id: str, 
            task_id: str, 
            payload: WorkflowTaskUpdate,
            user_id: str
        ) -> WorkflowTaskUpdateResponse:
        
            log = logger.bind(
                execution_id=execution_id,
                task_id=task_id,
                user_id=user_id
            )
            log.info("update task initiated")
            try:
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
                new_status = payload.status

                if current_status != new_status:  # Only validate if status is changing
                    allowed_statuses = VALID_TRANSITIONS.get(current_status, [])
                    if new_status not in allowed_statuses:
                        raise HTTPException(
                            status_code = status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid transition: {current_status} -> {new_status}"
                        )
                # 3. Update the specific task
                task.workflow_status = new_status
                if payload.output is not None:
                    task.workflow_task_output = payload.output
                task.updated_by = user_id
                # updated_at is handled by SQLAlchemy onupdate=func.now()
                query = (
                    update(WorkflowTaskExecution)
                    .where(
                        WorkflowTaskExecution.workflow_execution_id == execution_id,
                        WorkflowTaskExecution.workflow_task_id == task_id
                    )
                    .values(
                        workflow_status=payload.status,
                        workflow_task_output=payload.output,
                        updated_by=user_id,
                        updated_at=func.now()
                    )
                    .returning(WorkflowTaskExecution)
                )
                
                result = await db.execute(query)
                updated_task = result.scalars().first()
                
                if not updated_task:
                    log.warning("update task not found")
                    return None

                # 2. Production Logic: If task is completed, you might want to 
                # check if the whole workflow should transition status.
                # await self._refresh_workflow_status(db, execution_id)
                #self._trigger_next_tasks(db, metadata_service, execution_id, task_id, task.workflow_defn_id, user_id)
                log.info("Retrieving execution")
                wf_exec_query = (
                    select(WorkflowExecution)
                    .where(WorkflowExecution.workflow_execution_id == execution_id)
                )
                wf_exec_result = await db.execute(wf_exec_query)
                wf_exec = wf_exec_result.scalar_one_or_none()
                metadata = await metadata_service.get(db, task.workflow_defn_id)
                wf_defn = metadata.workflow_defn
                
                completed_tasks = await self.get_completed_tasks_for_execution(db, execution_id)
                log.info("Initiating next steps in workflow")
                await self.orchestrate_next_steps(db=db, publisher=publisher, execution_id=execution_id,
                                            defn_id=task.workflow_defn_id, workflow_defn=wf_defn,
                                            workflow_input=wf_exec.workflow_input, completed_tasks=completed_tasks,
                                            current_completed_id=task_id, user_id=user_id)
                log.info("Triggered next steps in workflow")
                await db.commit()
                resp = WorkflowTaskUpdateResponse(workflow_task_id=task_id)
                return resp
            except Exception as e:
                # Only rollback if the actual database logic itself crashed
                await db.rollback()
                log.error(f"Workflow execution engine crashed: {e}")
                return None
                
    
    
    async def orchestrate_next_steps(
        self,
        db,
        publisher,
        execution_id,
        defn_id,
        user_id,
        workflow_defn: dict,
        workflow_input: dict,
        completed_tasks: list, # List of WorkflowTaskExecution objects from DB
        current_completed_id: str
    ):
        log = logger.bind(
                execution_id=execution_id,
                task_id=current_completed_id,
                user_id=user_id
            )
        # 1. Map of completed IDs for DAG parsing
        completed_ids = {t.workflow_task_id for t in completed_tasks}
        
        # 2. Map of Task Name -> Outputs for Input Resolution
        # We use task_name as per your fetch_key logic <task_name>.<output_name>
        completed_outputs = {
            t.task_name: t.workflow_task_output 
            for t in completed_tasks 
            if t.workflow_task_output
        }
        all_tasks = await self.get_tasks_for_execution(db=db, execution_id=execution_id)
        in_progress_ids = {
            t.workflow_task_id for t in all_tasks 
            if t.workflow_status in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]
        }
        failed_ids = {t.workflow_task_id for t in all_tasks if t.workflow_status == WorkflowStatus.FAILED}

        # 3. Find what should run next
        ready_nodes = find_next_tasks(
            workflow_defn=workflow_defn, 
            completed_task_ids=completed_ids,
            in_progress_task_ids=in_progress_ids,
            failed_task_ids=failed_ids
        )
        log.info("ready_nodes")
        log.info(ready_nodes)
        
        if not ready_nodes:
            # No ready nodes? Check if we should close the workflow
            log.info("No ready nodes, completing workflow check")
            
            await self.check_and_complete_workflow(db, execution_id, ready_nodes, all_tasks)
            return
        
        try:
        
            for node in ready_nodes:
                if node["type"] == "TASK":
                    # Resolve inputs for the tasks
                    log.info("completed_outputs")
                    log.info(completed_outputs)
                    resolved_inputs = resolve_task_inputs(
                        current_task_input=node.get("input", []),
                        workflow_input=workflow_input,
                        completed_tasks_outputs=completed_outputs
                    )
                    
                    # Update the node with resolved values for the execution service
                    node["input"] = resolved_inputs
                    
                    # Trigger execution logic (publisher, DB record, etc.)
                    log.info("initiating task execution")
                    await self.execute_task(db, publisher, execution_id, defn_id, node, user_id)
                    
                elif node["type"] == "TASK_GROUP":
                    # If a group is ready, usually you'd trigger its first internal tasks
                    # by adding the Group ID to completed or marking it as 'STARTED'
                    log.info("Handling Task Group")
                    group_tasks = node.get("tasks", [])
                    for task_in_group in group_tasks:
                        # Assuming group members are of type TASK
                        await self.execute_task(db, publisher, execution_id, defn_id, task_in_group, user_id)
                    pass
        except WorkflowDependencyError as e:
            logger.error(f"Workflow {execution_id} failed due to dependency error: {e}")
            # Update parent workflow status to FAILED
            await self.update_execution_status(db, execution_id, WorkflowStatus.FAILED, user_id)
            
    
    async def check_and_complete_workflow(
        self, 
        db: AsyncSession, 
        execution_id: str, 
        ready_nodes: list, 
        all_tasks_in_db: list[WorkflowTaskExecution]
    ):
        
        log = logger.bind(
                execution_id=execution_id
            )
        
        # 1. If there are ready nodes, we aren't done yet
        if len(ready_nodes) > 0:
            return

        # 2. Check if any tasks are still in progress (RUNNING or PENDING)
        active_tasks = [
            t for t in all_tasks_in_db 
            if t.workflow_status in [WorkflowStatus.RUNNING, WorkflowStatus.PENDING]
        ]
        
        if not active_tasks:
            # 3. Everything is finished. Update the parent execution status.
            
            log.info(f"No more tasks to orchestrate. Marking workflow {execution_id} as COMPLETED.")
            
            await db.execute(
                update(WorkflowExecution)
                .where(WorkflowExecution.workflow_execution_id == execution_id)
                .values(
                    workflow_status=WorkflowStatus.COMPLETED
                )
            )
    
    '''async def _trigger_next_tasks(
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
                        await self.execute_task(db, execution_id, defn_id, sub_task, user_id)'''

    '''async def _evaluate_and_run(self, db, execution_id, defn_id, task_data, completed_id, user_id):
        """Checks if a task should run based on the task that just finished."""
        run_after = task_data.get("run_after", [])
        
        if completed_id in run_after:
            # Production Logic: In a real DAG, you'd check if ALL dependencies 
            # in 'run_after' are COMPLETED before starting this one.
            # For now, we trigger if the direct parent is done.
            
            completed_outputs = {
                t.task_name: t.workflow_task_output 
                for t in all_tasks 
                if t.workflow_status == WorkflowStatus.COMPLETED
            }

            # 2. Resolve the input for the next task
            resolved_input_list = resolve_task_inputs(
                current_task_input=task_defn["input"],
                workflow_input=workflow_execution.input_data,
                completed_tasks_outputs=completed_outputs
            )
            await self.execute_task(db, execution_id, defn_id, task_data, user_id)'''
            
    async def get_completed_tasks_for_execution(
        self, 
        db: AsyncSession, 
        execution_id: str
    ) -> list[WorkflowTaskExecution]:
        """
        Fetches all successfully finished tasks for a specific workflow execution.
        """
        query = (
            select(WorkflowTaskExecution)
            .where(
                WorkflowTaskExecution.workflow_execution_id == execution_id,
                WorkflowTaskExecution.workflow_status == WorkflowStatus.COMPLETED
            )
        )
        
        result = await db.execute(query)
        # return result.scalars().all() gives you the list of objects
        return list(result.scalars().all())
    
    async def get_tasks_for_execution(
        self, 
        db: AsyncSession, 
        execution_id: str
    ) -> list[WorkflowTaskExecution]:
        """
        Fetches all tasks for a specific workflow execution.
        """
        query = (
            select(WorkflowTaskExecution)
            .where(
                WorkflowTaskExecution.workflow_execution_id == execution_id
            )
        )
        
        result = await db.execute(query)
        # return result.scalars().all() gives you the list of objects
        return list(result.scalars().all())
    
           
    async def get_task_execution(
        self, 
        db: AsyncSession, 
        execution_id: str, 
        task_id: str
    ) -> WorkflowTaskExecution | None:
        """
        Business logic to retrieve a specific task execution.
        """
        query = select(WorkflowTaskExecution).where(
            WorkflowTaskExecution.workflow_execution_id == execution_id,
            WorkflowTaskExecution.workflow_task_id == task_id
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_task_executions(
        self, 
        db: AsyncSession, 
        execution_id: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> Sequence[WorkflowTaskExecution]:
        """
        Retrieves a paginated list of tasks for a specific execution.
        """
        query = (
            select(WorkflowTaskExecution)
            .where(WorkflowTaskExecution.workflow_execution_id == execution_id)
            .offset(offset)
            .limit(limit)
            # Ordering by primary key or created_at ensures consistent pagination
            .order_by(WorkflowTaskExecution.workflow_task_id)
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    
    async def get_execution_by_id(
        self, 
        db: AsyncSession, 
        execution_id: str
    ) -> WorkflowExecution | None:
        """
        Retrieves a workflow execution record.
        """
        query = (
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_execution_id == execution_id)
        )
        
        result = await db.execute(query)
        # unique() is required when using joinedload with scalars
        return result.unique().scalar_one_or_none()
    
    
    async def update_execution_status(
        self, 
        db: AsyncSession, 
        execution_id: str,
        status: str,
        user_id: str
    ) -> WorkflowExecution | None:
        """
        updates workflow executions status
        """
    
        await db.execute(
                    update(WorkflowExecution)
                    .where(WorkflowExecution.workflow_execution_id == execution_id)
                    .values(workflow_status=status, updated_by=user_id)
                )

workflow_execution_service = WorkflowExecutionService()