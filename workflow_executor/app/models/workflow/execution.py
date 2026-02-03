from datetime import datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import String, ForeignKey, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.workflow.status import WorkflowStatus  # Assuming Enum is in a shared file

if TYPE_CHECKING:
    from .metadata import WorkflowMetadata
    from .task import WorkflowTaskExecution

class WorkflowExecution(Base):
    __tablename__ = "workflow_execution"

    workflow_execution_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_defn_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflow_metadata.workflow_defn_id"), nullable=False
    )
    
    workflow_status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False
    )
    workflow_input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    workflow_output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)

    # Relationships
    workflow_metadata: Mapped["WorkflowMetadata"] = relationship(
        "WorkflowMetadata", back_populates="executions"
    )
    tasks: Mapped[list["WorkflowTaskExecution"]] = relationship(
        "WorkflowTaskExecution", back_populates="execution", cascade="all, delete-orphan"
    )