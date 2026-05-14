"""Generic async repository — Repository Pattern."""
import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.db_models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Optional[ModelType]:
        result = await self.session.execute(select(self.model).where(self.model.id == entity_id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 50) -> List[ModelType]:
        result = await self.session.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, entity_id: uuid.UUID, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        await self.session.execute(
            update(self.model).where(self.model.id == entity_id).values(**obj_in)
        )
        return await self.get_by_id(entity_id)

    async def delete(self, entity_id: uuid.UUID) -> bool:
        obj = await self.get_by_id(entity_id)
        if not obj:
            return False
        await self.session.delete(obj)
        return True
