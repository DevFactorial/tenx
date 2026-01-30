
from datetime import datetime, timezone
from sqlalchemy import func, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    # created_at: Set by DB on row insertion
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        nullable=False
    )
    
    # updated_at: Set by DB on insertion and updated by SQLAlchemy on every save
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=True)