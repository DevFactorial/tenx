from datetime import datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import String, ForeignKey, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.workflow.status import WorkflowStatus

if TYPE_CHECKING:
    from .execution import WorkflowExecution

class WorkflowTaskExecution(Base):
    __tablename__ = "workflow_task_execution"

    # Composite Primary Key
    workflow_execution_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflow_execution.workflow_execution_id"), primary_key=True
    )
    workflow_task_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_name: Mapped[str] = mapped_column(String)
    
    workflow_defn_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflow_metadata.workflow_defn_id"), nullable=False
    )
    
    #workflow_task_type: Mapped[str] = mapped_column(String, nullable=False) # Maps to your "workflow_task_task"
    workflow_status: Mapped[WorkflowStatus] = mapped_column(Enum(WorkflowStatus), nullable=False)
    
    workflow_task_input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    workflow_task_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution", back_populates="tasks"
    )