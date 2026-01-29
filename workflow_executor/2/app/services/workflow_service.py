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

# State Machine Configuration
VALID_TRANSITIONS = {
    WorkflowStatus.PENDING: [WorkflowStatus.RUNNING, WorkflowStatus.FAILED],
    WorkflowStatus.RUNNING: [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED],
    WorkflowStatus.COMPLETED: [],  # Terminal state: no further changes allowed
    WorkflowStatus.FAILED: [WorkflowStatus.PENDING], # Only allowed if retrying
}


class WorkflowExecutionService:
    async def execute(
        self, db: AsyncSession, payload: WorkflowExecutionCreate, user_id: str
    ) -> WorkflowExecution:
        # 1. Initialize the execution record
        execution_id = f"wf_exec_{uuid.uuid4().hex[:12]}"
        
        db_obj = WorkflowExecution(
            workflow_execution_id=execution_id,
            workflow_defn_id=payload.workflow_defn_id,
            workflow_input=payload.workflow_input,
            workflow_status=WorkflowStatus.PENDING,
            created_by=user_id,
            updated_by=user_id
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # 2. Logic to trigger the actual background worker would go here
        # await start_workflow_engine(execution_id)
        
        return db_obj
    
    async def update_task(
            self, 
            db: AsyncSession, 
            *, 
            execution_id: str, 
            task_id: str, 
            payload: WorkflowTaskUpdate,
            user_id: str
        ) -> WorkflowTaskExecution | None:
            # 1. Update the specific task
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

workflow_execution_service = WorkflowExecutionService()