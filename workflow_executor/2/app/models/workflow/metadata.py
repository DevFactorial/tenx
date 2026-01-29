from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING, Any
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
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    updated_by: Mapped[str] = mapped_column(String)