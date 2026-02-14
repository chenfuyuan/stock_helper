from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    通用 CRUD 仓储基类
    提供基本的增删改查操作实现
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> Optional[ModelType]:
        """根据 ID 获取单个记录"""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        obj = result.scalars().first()
        if not obj:
            logger.debug(f"{self.model.__name__} with id {id} not found")
        return obj

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """获取分页列表"""
        logger.debug(f"Fetching {self.model.__name__} list: skip={skip}, limit={limit}")
        result = await self.session.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, obj_in: dict) -> ModelType:
        """创建新记录"""
        logger.debug(f"Creating {self.model.__name__}")
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        logger.info(f"Created {self.model.__name__} with id {db_obj.id}")
        return db_obj

    async def update(self, id: UUID, obj_in: dict) -> Optional[ModelType]:
        """更新记录"""
        logger.debug(f"Updating {self.model.__name__} with id {id}")
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        return await self.get(id)

    async def delete(self, id: UUID) -> bool:
        """删除记录"""
        logger.debug(f"Deleting {self.model.__name__} with id {id}")
        result = await self.session.execute(delete(self.model).where(self.model.id == id))
        await self.session.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted {self.model.__name__} with id {id}")
            return True
        logger.warning(f"Delete failed: {self.model.__name__} with id {id} not found")
        return False

    async def upsert_all(
        self,
        items: List[dict],
        unique_fields: List[str],
        exclude_fields: List[str] = None,
    ) -> int:
        """
        通用的批量 Upsert (Insert or Update) 方法
        基于 PostgreSQL 的 ON CONFLICT DO UPDATE

        :param items: 待插入的数据字典列表
        :param unique_fields: 唯一约束的字段列表，用于判断冲突
        :param exclude_fields: 更新时需要排除的字段（如 created_at）
        :return: 插入或更新的行数
        """
        if not items:
            return 0

        if exclude_fields is None:
            exclude_fields = ["created_at"]

        # 批量处理，避免一次性插入过多数据
        batch_size = 1000
        total_count = 0

        logger.info(f"Starting bulk upsert for {self.model.__name__}, total items: {len(items)}")

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            stmt = insert(self.model).values(batch)

            # 构建 update 语句，排除不需要更新的字段
            update_dict = {col.name: col for col in stmt.excluded if col.name not in exclude_fields}

            if update_dict:
                stmt = stmt.on_conflict_do_update(index_elements=unique_fields, set_=update_dict)
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=unique_fields)

            result = await self.session.execute(stmt)
            total_count += result.rowcount

        await self.session.commit()
        logger.info(f"Bulk upsert completed for {self.model.__name__}: {total_count} rows affected")
        return total_count
