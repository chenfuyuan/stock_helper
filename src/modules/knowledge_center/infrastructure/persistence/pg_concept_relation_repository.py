"""
概念关系 PostgreSQL 仓储实现。

实现 IConceptRelationRepository 接口，提供 concept_relation 表的 CRUD 操作。
"""

from datetime import datetime

from loguru import logger
from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.knowledge_center.domain.model.concept_relation import ConceptRelation
from src.modules.knowledge_center.domain.ports.concept_relation_repository import (
    IConceptRelationRepository,
)
from src.modules.knowledge_center.infrastructure.persistence.concept_relation_model import (
    ConceptRelationModel,
)


class PgConceptRelationRepository(IConceptRelationRepository):
    """
    概念关系 PostgreSQL 仓储实现。
    
    使用 SQLAlchemy 操作 concept_relation 表，作为 Single Source of Truth。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化仓储。
        
        Args:
            session: SQLAlchemy 异步会话
        """
        self.session = session

    async def create(self, relation: ConceptRelation) -> ConceptRelation:
        """创建新的概念关系记录。"""
        now = datetime.now()
        db_obj = ConceptRelationModel(
            source_concept_code=relation.source_concept_code,
            target_concept_code=relation.target_concept_code,
            relation_type=relation.relation_type,
            source_type=relation.source_type,
            status=relation.status,
            confidence=relation.confidence,
            ext_info=relation.ext_info,
            created_by=relation.created_by,
            created_at=now,
            updated_at=now,
        )
        
        try:
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            logger.info(
                f"创建概念关系: {db_obj.source_concept_code} -> "
                f"{db_obj.target_concept_code} ({db_obj.relation_type}), id={db_obj.id}"
            )
            return self._to_entity(db_obj)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"创建概念关系失败（唯一约束冲突）: {e}")
            raise

    async def get_by_id(self, relation_id: int) -> ConceptRelation | None:
        """根据 ID 查询单条概念关系记录。"""
        result = await self.session.execute(
            select(ConceptRelationModel).where(ConceptRelationModel.id == relation_id)
        )
        db_obj = result.scalars().first()
        if not db_obj:
            logger.debug(f"概念关系记录不存在: id={relation_id}")
            return None
        return self._to_entity(db_obj)

    async def list_relations(
        self,
        source_concept_code: str | None = None,
        target_concept_code: str | None = None,
        relation_type: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConceptRelation]:
        """列表查询概念关系，支持多条件筛选。"""
        filters = []
        if source_concept_code:
            filters.append(ConceptRelationModel.source_concept_code == source_concept_code)
        if target_concept_code:
            filters.append(ConceptRelationModel.target_concept_code == target_concept_code)
        if relation_type:
            filters.append(ConceptRelationModel.relation_type == relation_type)
        if source_type:
            filters.append(ConceptRelationModel.source_type == source_type)
        if status:
            filters.append(ConceptRelationModel.status == status)

        query = select(ConceptRelationModel)
        if filters:
            query = query.where(and_(*filters))
        query = query.offset(offset).limit(limit).order_by(ConceptRelationModel.id.desc())

        result = await self.session.execute(query)
        db_objs = result.scalars().all()
        logger.debug(f"查询概念关系列表，返回 {len(db_objs)} 条记录")
        return [self._to_entity(obj) for obj in db_objs]

    async def update(self, relation: ConceptRelation) -> ConceptRelation:
        """更新概念关系记录。"""
        if not relation.id:
            raise ValueError("更新操作需要提供 relation.id")

        result = await self.session.execute(
            select(ConceptRelationModel).where(ConceptRelationModel.id == relation.id)
        )
        db_obj = result.scalars().first()
        if not db_obj:
            raise ValueError(f"概念关系记录不存在: id={relation.id}")

        # 更新字段
        db_obj.status = relation.status
        db_obj.confidence = relation.confidence
        db_obj.ext_info = relation.ext_info
        db_obj.updated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(db_obj)
        logger.info(f"更新概念关系: id={db_obj.id}, status={db_obj.status}")
        return self._to_entity(db_obj)

    async def delete(self, relation_id: int) -> bool:
        """删除概念关系记录。"""
        result = await self.session.execute(
            delete(ConceptRelationModel).where(ConceptRelationModel.id == relation_id)
        )
        await self.session.commit()
        if result.rowcount > 0:
            logger.info(f"删除概念关系: id={relation_id}")
            return True
        logger.warning(f"删除概念关系失败（记录不存在）: id={relation_id}")
        return False

    async def batch_create(self, relations: list[ConceptRelation]) -> list[ConceptRelation]:
        """
        批量创建概念关系记录。
        
        跳过违反唯一约束的记录，继续处理其他记录。
        """
        if not relations:
            return []

        now = datetime.now()
        values = [
            {
                "source_concept_code": r.source_concept_code,
                "target_concept_code": r.target_concept_code,
                "relation_type": r.relation_type,
                "source_type": r.source_type,
                "status": r.status,
                "confidence": r.confidence,
                "ext_info": r.ext_info,
                "created_by": r.created_by,
                "created_at": now,
                "updated_at": now,
            }
            for r in relations
        ]

        stmt = insert(ConceptRelationModel).values(values)
        # 遇到唯一约束冲突时跳过（DO NOTHING）
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["source_concept_code", "target_concept_code", "relation_type"]
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        
        inserted_count = result.rowcount
        skipped_count = len(relations) - inserted_count
        logger.info(
            f"批量创建概念关系: 成功 {inserted_count} 条，跳过（重复）{skipped_count} 条"
        )

        # 返回成功插入的记录（根据输入条件查询）
        # 简化实现：返回空列表，调用方可根据需要重新查询
        return []

    async def get_all_confirmed(self) -> list[ConceptRelation]:
        """获取所有已确认的概念关系记录。"""
        result = await self.session.execute(
            select(ConceptRelationModel)
            .where(ConceptRelationModel.status == "CONFIRMED")
            .order_by(ConceptRelationModel.id)
        )
        db_objs = result.scalars().all()
        logger.debug(f"查询所有已确认概念关系，共 {len(db_objs)} 条")
        return [self._to_entity(obj) for obj in db_objs]

    async def count(
        self,
        source_concept_code: str | None = None,
        target_concept_code: str | None = None,
        relation_type: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        """统计概念关系记录数量，支持多条件筛选。"""
        filters = []
        if source_concept_code:
            filters.append(ConceptRelationModel.source_concept_code == source_concept_code)
        if target_concept_code:
            filters.append(ConceptRelationModel.target_concept_code == target_concept_code)
        if relation_type:
            filters.append(ConceptRelationModel.relation_type == relation_type)
        if source_type:
            filters.append(ConceptRelationModel.source_type == source_type)
        if status:
            filters.append(ConceptRelationModel.status == status)

        query = select(ConceptRelationModel)
        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        count = len(result.scalars().all())
        logger.debug(f"概念关系记录统计: {count} 条")
        return count

    def _to_entity(self, db_obj: ConceptRelationModel) -> ConceptRelation:
        """
        将数据库模型转换为领域实体。
        
        Args:
            db_obj: SQLAlchemy 模型对象
        
        Returns:
            ConceptRelation 领域实体
        """
        return ConceptRelation(
            id=db_obj.id,
            source_concept_code=db_obj.source_concept_code,
            target_concept_code=db_obj.target_concept_code,
            relation_type=db_obj.relation_type,
            source_type=db_obj.source_type,
            status=db_obj.status,
            confidence=db_obj.confidence,
            ext_info=db_obj.ext_info,
            created_by=db_obj.created_by,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
        )
