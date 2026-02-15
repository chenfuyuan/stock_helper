"""
概念关系应用服务。

聚合概念关系的 CRUD 操作，提供 ext_info 校验和业务逻辑封装。
"""

from datetime import datetime

from loguru import logger
from pydantic import ValidationError

from src.modules.knowledge_center.domain.dtos.concept_relation_ext_info_dtos import (
    LLMExtInfo,
    ManualExtInfo,
)
from src.modules.knowledge_center.domain.model.concept_relation import ConceptRelation
from src.modules.knowledge_center.domain.model.enums import (
    RelationSourceType,
    RelationStatus,
)
from src.modules.knowledge_center.domain.ports.concept_relation_repository import (
    IConceptRelationRepository,
)


class ConceptRelationService:
    """
    概念关系应用服务。
    
    提供概念关系的 CRUD 操作，包含 ext_info 校验、业务规则验证等。
    """

    def __init__(self, repository: IConceptRelationRepository):
        """
        初始化服务。
        
        Args:
            repository: 概念关系仓储实例
        """
        self._repo = repository

    async def create_manual_relation(
        self,
        source_concept_code: str,
        target_concept_code: str,
        relation_type: str,
        note: str | None = None,
        reason: str | None = None,
        created_by: str | None = None,
    ) -> ConceptRelation:
        """
        创建手动关系。
        
        手动创建的关系默认 status=CONFIRMED, confidence=1.0，
        ext_info 使用 ManualExtInfo 结构。
        
        Args:
            source_concept_code: 源概念代码
            target_concept_code: 目标概念代码
            relation_type: 关系类型
            note: 用户备注说明
            reason: 建立关系的理由
            created_by: 创建人标识
        
        Returns:
            创建后的概念关系实体
        
        Raises:
            ValidationError: 如果 ext_info 校验失败
            IntegrityError: 如果违反唯一约束
        """
        # 构建并校验 ext_info
        ext_info_obj = ManualExtInfo(note=note, reason=reason)
        ext_info = ext_info_obj.model_dump(mode="json", exclude_none=True)

        # 创建实体
        relation = ConceptRelation(
            source_concept_code=source_concept_code,
            target_concept_code=target_concept_code,
            relation_type=relation_type,
            source_type=RelationSourceType.MANUAL,
            status=RelationStatus.CONFIRMED,  # 手动创建直接确认
            confidence=1.0,
            ext_info=ext_info,
            created_by=created_by,
        )

        created = await self._repo.create(relation)
        logger.info(
            f"创建手动概念关系: {source_concept_code} -> {target_concept_code} "
            f"({relation_type}), id={created.id}"
        )
        return created

    async def create_llm_relation(
        self,
        source_concept_code: str,
        target_concept_code: str,
        relation_type: str,
        confidence: float,
        model: str,
        prompt: str,
        raw_output: str,
        parsed_result: dict,
        reasoning: str,
        model_version: str | None = None,
        batch_id: str | None = None,
        created_by: str | None = None,
    ) -> ConceptRelation:
        """
        创建 LLM 推荐关系。
        
        LLM 推荐的关系默认 status=PENDING，需人工确认，
        ext_info 使用 LLMExtInfo 结构，记录完整追溯信息。
        
        Args:
            source_concept_code: 源概念代码
            target_concept_code: 目标概念代码
            relation_type: 关系类型
            confidence: 置信度
            model: LLM 模型名称
            prompt: 完整输入 prompt
            raw_output: LLM 原始输出
            parsed_result: 解析后的分析结果
            reasoning: 推理依据
            model_version: 模型版本
            batch_id: 批次 ID
            created_by: 创建人标识
        
        Returns:
            创建后的概念关系实体
        
        Raises:
            ValidationError: 如果 ext_info 校验失败
            IntegrityError: 如果违反唯一约束
        """
        # 构建并校验 ext_info
        ext_info_obj = LLMExtInfo(
            model=model,
            model_version=model_version,
            prompt=prompt,
            raw_output=raw_output,
            parsed_result=parsed_result,
            reasoning=reasoning,
            batch_id=batch_id,
            analyzed_at=datetime.now(),
        )
        ext_info = ext_info_obj.model_dump(mode="json", exclude_none=True)

        # 创建实体
        relation = ConceptRelation(
            source_concept_code=source_concept_code,
            target_concept_code=target_concept_code,
            relation_type=relation_type,
            source_type=RelationSourceType.LLM,
            status=RelationStatus.PENDING,  # LLM 推荐需人工确认
            confidence=confidence,
            ext_info=ext_info,
            created_by=created_by,
        )

        created = await self._repo.create(relation)
        logger.info(
            f"创建 LLM 推荐关系: {source_concept_code} -> {target_concept_code} "
            f"({relation_type}), id={created.id}, confidence={confidence}"
        )
        return created

    async def get_by_id(self, relation_id: int) -> ConceptRelation | None:
        """
        根据 ID 查询单条概念关系。
        
        Args:
            relation_id: 关系记录 ID
        
        Returns:
            概念关系实体，不存在时返回 None
        """
        return await self._repo.get_by_id(relation_id)

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
            offset: 偏移量
        
        Returns:
            概念关系实体列表
        """
        return await self._repo.list_relations(
            source_concept_code=source_concept_code,
            target_concept_code=target_concept_code,
            relation_type=relation_type,
            source_type=source_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def update_status(
        self, relation_id: int, new_status: str
    ) -> ConceptRelation:
        """
        更新关系状态（用于确认或拒绝 LLM 推荐）。
        
        Args:
            relation_id: 关系记录 ID
            new_status: 新状态（CONFIRMED / REJECTED）
        
        Returns:
            更新后的实体
        
        Raises:
            ValueError: 如果记录不存在
        """
        relation = await self._repo.get_by_id(relation_id)
        if not relation:
            raise ValueError(f"概念关系记录不存在: id={relation_id}")

        relation.status = new_status
        updated = await self._repo.update(relation)
        
        logger.info(f"更新概念关系状态: id={relation_id}, status={new_status}")
        return updated

    async def delete(self, relation_id: int) -> bool:
        """
        删除概念关系记录。
        
        Args:
            relation_id: 关系记录 ID
        
        Returns:
            是否删除成功
        """
        success = await self._repo.delete(relation_id)
        if success:
            logger.info(f"删除概念关系: id={relation_id}")
        return success

    async def count(
        self,
        source_concept_code: str | None = None,
        target_concept_code: str | None = None,
        relation_type: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        """
        统计概念关系记录数量。
        
        Args:
            source_concept_code: 源概念代码筛选
            target_concept_code: 目标概念代码筛选
            relation_type: 关系类型筛选
            source_type: 来源类型筛选
            status: 状态筛选
        
        Returns:
            符合条件的记录数量
        """
        return await self._repo.count(
            source_concept_code=source_concept_code,
            target_concept_code=target_concept_code,
            relation_type=relation_type,
            source_type=source_type,
            status=status,
        )

    def validate_manual_ext_info(self, ext_info: dict) -> bool:
        """
        校验手动创建关系的 ext_info 结构。
        
        Args:
            ext_info: 待校验的 ext_info 字典
        
        Returns:
            是否通过校验
        
        Raises:
            ValidationError: 如果校验失败
        """
        ManualExtInfo(**ext_info)
        return True

    def validate_llm_ext_info(self, ext_info: dict) -> bool:
        """
        校验 LLM 推荐关系的 ext_info 结构。
        
        Args:
            ext_info: 待校验的 ext_info 字典
        
        Returns:
            是否通过校验
        
        Raises:
            ValidationError: 如果校验失败
        """
        LLMExtInfo(**ext_info)
        return True
