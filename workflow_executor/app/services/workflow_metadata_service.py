from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import WorkflowMetadata
from app.schemas.metadata import WorkflowMetadataCreate, WorkflowMetadataUpdate
import uuid

class WorkflowMetadataService:
    async def create(
        self, db: AsyncSession, *, obj_in: WorkflowMetadataCreate, user_id: str
    ) -> WorkflowMetadata:
        defn_data = obj_in.workflow_defn.model_dump(mode='json')
        db_obj = WorkflowMetadata(
            workflow_defn_id=f"wf_{uuid.uuid4().hex[:8]}",
            name=obj_in.name,
            description=obj_in.description,
            workflow_defn=defn_data, # Serialization
            run_schedule=obj_in.run_schedule,
            created_by=user_id,
            updated_by=user_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, workflow_defn_id: str) -> Optional[WorkflowMetadata]:
        result = await db.execute(
            select(WorkflowMetadata).where(WorkflowMetadata.workflow_defn_id == workflow_defn_id)
        )
        return result.scalars().first()
    
    async def get_by_name(self, db: AsyncSession, name: str) -> WorkflowMetadata | None:
        """
        Fetch a single workflow metadata record by its name.
        """
        # 1. Create the select statement
        query = select(WorkflowMetadata).where(WorkflowMetadata.name == name)
        
        # 2. Execute the query
        result = await db.execute(query)
        
        # 3. Return the first result or None
        return result.scalars().first()

    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 10, 
        name: Optional[str] = None
    ) -> Sequence[WorkflowMetadata]:
        query = select(WorkflowMetadata)
        if name:
            query = query.where(WorkflowMetadata.name.ilike(f"%{name}%"))
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def update(
        self, 
        db: AsyncSession, 
        *, 
        workflow_defn_id: str, 
        obj_in: WorkflowMetadataUpdate, 
        user_id: str
    ) -> Optional[WorkflowMetadata]:
        db_obj = await self.get(db, workflow_defn_id)
        if not db_obj:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db_obj.updated_by = user_id
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, workflow_defn_id: str) -> Optional[WorkflowMetadata]:
        db_obj = await self.get(db, workflow_defn_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj

metadata_service = WorkflowMetadataService()