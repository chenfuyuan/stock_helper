"""
概念关系实体单元测试。

测试 ConceptRelation 的默认值逻辑、枚举值完整性和业务规则。
"""

import pytest
from pydantic import ValidationError

from src.modules.knowledge_center.domain.model.concept_relation import ConceptRelation
from src.modules.knowledge_center.domain.model.enums import (
    ConceptRelationType,
    RelationSourceType,
    RelationStatus,
)


class TestConceptRelation:
    """概念关系实体测试类。"""

    def test_minimal_creation(self):
        """测试最小字段创建概念关系。"""
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
        )

        assert relation.source_concept_code == "TECH"
        assert relation.target_concept_code == "AI"
        assert relation.relation_type == ConceptRelationType.IS_UPSTREAM_OF
        assert relation.source_type == RelationSourceType.MANUAL
        assert relation.status == RelationStatus.PENDING  # 默认值
        assert relation.confidence == 1.0  # 默认值
        assert relation.ext_info == {}  # 默认值
        assert relation.created_by is None
        assert relation.id is None
        assert relation.created_at is None
        assert relation.updated_at is None

    def test_manual_relation_defaults(self):
        """测试手动创建关系的默认值。"""
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
        )

        # 手动创建的关系应该有合理的默认值
        assert relation.confidence == 1.0
        assert relation.status == RelationStatus.PENDING  # 由业务层设置为 CONFIRMED

    def test_llm_relation_defaults(self):
        """测试 LLM 推荐关系的默认值。"""
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.LLM,
            confidence=0.8,
        )

        assert relation.confidence == 0.8
        assert relation.status == RelationStatus.PENDING  # LLM 推荐默认待确认

    def test_confidence_validation(self):
        """测试置信度范围验证。"""
        # 有效范围
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
            confidence=0.5,
        )
        assert relation.confidence == 0.5

        # 边界值
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
            confidence=0.0,
        )
        assert relation.confidence == 0.0

        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
            confidence=1.0,
        )
        assert relation.confidence == 1.0

        # 超出范围
        with pytest.raises(ValidationError):
            ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type=ConceptRelationType.IS_UPSTREAM_OF,
                source_type=RelationSourceType.MANUAL,
                confidence=-0.1,
            )

        with pytest.raises(ValidationError):
            ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type=ConceptRelationType.IS_UPSTREAM_OF,
                source_type=RelationSourceType.MANUAL,
                confidence=1.1,
            )

    def test_enum_values_completeness(self):
        """测试枚举值完整性。"""
        # 测试所有关系类型
        for rel_type in ConceptRelationType:
            relation = ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type=rel_type,
                source_type=RelationSourceType.MANUAL,
            )
            assert relation.relation_type == rel_type

        # 测试所有来源类型
        for source_type in RelationSourceType:
            relation = ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type=ConceptRelationType.IS_UPSTREAM_OF,
                source_type=source_type,
            )
            assert relation.source_type == source_type

        # 测试所有状态
        for status in RelationStatus:
            relation = ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type=ConceptRelationType.IS_UPSTREAM_OF,
                source_type=RelationSourceType.MANUAL,
                status=status,
            )
            assert relation.status == status

    def test_ext_info_handling(self):
        """测试扩展信息处理。"""
        ext_info = {"note": "测试备注", "reason": "测试原因"}
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
            ext_info=ext_info,
        )

        assert relation.ext_info == ext_info

        # 空字典默认值
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
        )
        assert relation.ext_info == {}

    def test_required_fields_validation(self):
        """测试必填字段验证。"""
        # 缺少必填字段应该抛出 ValidationError
        with pytest.raises(ValidationError):
            ConceptRelation()

        with pytest.raises(ValidationError):
            ConceptRelation(source_concept_code="TECH")

        with pytest.raises(ValidationError):
            ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
            )

        with pytest.raises(ValidationError):
            ConceptRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            )

    def test_model_dump(self):
        """测试模型序列化。"""
        relation = ConceptRelation(
            source_concept_code="TECH",
            target_concept_code="AI",
            relation_type=ConceptRelationType.IS_UPSTREAM_OF,
            source_type=RelationSourceType.MANUAL,
            confidence=0.8,
            ext_info={"note": "测试"},
        )

        data = relation.model_dump()
        assert data["source_concept_code"] == "TECH"
        assert data["target_concept_code"] == "AI"
        assert data["relation_type"] == "IS_UPSTREAM_OF"
        assert data["source_type"] == "MANUAL"
        assert data["confidence"] == 0.8
        assert data["ext_info"] == {"note": "测试"}
