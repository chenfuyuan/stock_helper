"""
概念关系仓储 Port 接口。

定义概念关系的持久化抽象，供 Application 层调用。
"""

from abc import ABC, abstractmethod

from ..model.concept_relation import ConceptRelation


class IConceptRelationRepository(ABC):
    """
    概念关系仓储接口。
    
    PostgreSQL 为 Single Source of Truth，提供概念关系的完整 CRUD 操作。
    """

    @abstractmethod
    async def create(self, relation: ConceptRelation) -> ConceptRelation:
        """
        创建新的概念关系记录。
        
        Args:
            relation: 概念关系实体（不包含 id）
        
        Returns:
            创建后的实体（包含 id 和时间戳）
        
        Raises:
            IntegrityError: 如果违反唯一约束（source + target + type 重复）
        """
        pass

    @abstractmethod
    async def get_by_id(self, relation_id: int) -> ConceptRelation | None:
        """
        根据 ID 查询单条概念关系记录。
        
        Args:
            relation_id: 关系记录 ID
        
        Returns:
            概念关系实体，不存在时返回 None
        """
        pass

    @abstractmethod
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
        """
        列表查询概念关系，支持多条件筛选。
        
        Args:
            source_concept_code: 源概念代码筛选
            target_concept_code: 目标概念代码筛选
            relation_type: 关系类型筛选
            source_type: 来源类型筛选
            status: 状态筛选
            limit: 返回条数限制
            offset: 偏移量（分页）
        
        Returns:
            概念关系实体列表
        """
        pass

    @abstractmethod
    async def update(self, relation: ConceptRelation) -> ConceptRelation:
        """
        更新概念关系记录。
        
        Args:
            relation: 包含 id 和更新字段的实体
        
        Returns:
            更新后的实体
        
        Raises:
            ValueError: 如果记录不存在
        """
        pass

    @abstractmethod
    async def delete(self, relation_id: int) -> bool:
        """
        删除概念关系记录。
        
        Args:
            relation_id: 关系记录 ID
        
        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    async def batch_create(self, relations: list[ConceptRelation]) -> list[ConceptRelation]:
        """
        批量创建概念关系记录。
        
        跳过违反唯一约束的记录（已存在的关系），继续处理其他记录。
        
        Args:
            relations: 概念关系实体列表
        
        Returns:
            成功创建的实体列表（包含 id）
        """
        pass

    @abstractmethod
    async def get_all_confirmed(self) -> list[ConceptRelation]:
        """
        获取所有已确认的概念关系记录。
        
        用于同步到 Neo4j（全量重建或增量检查）。
        
        Returns:
            所有 status=CONFIRMED 的概念关系列表
        """
        pass

    @abstractmethod
    async def count(
        self,
        source_concept_code: str | None = None,
        target_concept_code: str | None = None,
        relation_type: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        """
        统计概念关系记录数量，支持多条件筛选。
        
        Args:
            source_concept_code: 源概念代码筛选
            target_concept_code: 目标概念代码筛选
            relation_type: 关系类型筛选
            source_type: 来源类型筛选
            status: 状态筛选
        
        Returns:
            符合条件的记录数量
        """
        pass
