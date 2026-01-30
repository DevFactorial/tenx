from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING, Any, List
from sqlalchemy import String, ForeignKey, DateTime, Enum, func, Text
from sqlalchemy.dialects.postgresql import JSONB

from  app.models.base import Base

class WorkflowMetadata(Base):
    __tablename__ = "workflow_metadata"

    workflow_defn_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_defn: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    run_schedule: Mapped[str | None] = mapped_column(String)
    
    executions: Mapped[List["WorkflowExecution"]] = relationship(
        "WorkflowExecution", 
        back_populates="workflow_metadata"
    )
    