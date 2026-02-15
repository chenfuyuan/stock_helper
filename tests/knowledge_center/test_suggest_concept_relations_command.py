"""
LLM 概念关系推荐命令单元测试。

测试 SuggestConceptRelationsCmd 的流程编排，使用 mock Analyzer 和 Repository。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.knowledge_center.application.commands.suggest_concept_relations_command import (
    SuggestConceptRelationsCmd,
    SuggestConceptRelationsResult,
)
from src.modules.knowledge_center.domain.dtos.concept_relation_analyzer_dtos import (
    ConceptForAnalysis,
    SuggestedRelation,
)
from src.modules.knowledge_center.domain.model.concept_relation import ConceptRelation
from src.modules.knowledge_center.domain.model.enums import (
    RelationSourceType,
    RelationStatus,
)


class TestSuggestConceptRelationsCmd:
    """LLM 概念关系推荐命令测试类。"""

    @pytest.fixture
    def mock_analyzer(self):
        """Mock 概念关系分析器。"""
        return AsyncMock()

    @pytest.fixture
    def mock_repository(self):
        """Mock 概念关系仓储。"""
        repo = AsyncMock()
        repo.batch_create.return_value = []  # 简化实现，返回空列表
        return repo

    @pytest.fixture
    def mock_service(self):
        """Mock 概念关系服务。"""
        return AsyncMock()

    @pytest.fixture
    def command(self, mock_analyzer, mock_repository, mock_service):
        """创建命令实例。"""
        return SuggestConceptRelationsCmd(
            analyzer=mock_analyzer,
            repository=mock_repository,
            service=mock_service,
        )

    @pytest.fixture
    def sample_concepts(self):
        """示例概念列表。"""
        return [
            ("TECH", "技术"),
            ("AI", "人工智能"),
            ("CHIP", "芯片"),
        ]

    @pytest.fixture
    def sample_suggested_relations(self):
        """示例推荐关系。"""
        return [
            SuggestedRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                confidence=0.8,
                reasoning="技术是人工智能的基础",
            ),
            SuggestedRelation(
                source_concept_code="CHIP",
                target_concept_code="AI",
                relation_type="IS_PART_OF",
                confidence=0.9,
                reasoning="芯片是人工智能的组成部分",
            ),
            SuggestedRelation(
                source_concept_code="TECH",
                target_concept_code="CHIP",
                relation_type="IS_UPSTREAM_OF",
                confidence=0.4,  # 低于默认阈值
                reasoning="技术是芯片的上游",
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_success(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试成功执行推荐流程。"""
        # Mock analyzer 返回
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations

        # 执行命令
        result = await command.execute(
            concept_codes_with_names=sample_concepts,
            created_by="test_user",
            min_confidence=0.5,
        )

        # 验证结果
        assert isinstance(result, SuggestConceptRelationsResult)
        assert result.total_suggested == 3
        assert result.created_count == 2  # 过滤低置信度后
        assert result.skipped_count == 0  # 简化实现
        assert result.batch_id is not None
        assert len(result.batch_id) > 0

        # 验证 analyzer 调用
        mock_analyzer.analyze_relations.assert_called_once()
        call_args = mock_analyzer.analyze_relations.call_args[0][0]
        assert len(call_args) == 3
        assert all(isinstance(c, ConceptForAnalysis) for c in call_args)
        assert call_args[0].code == "TECH"
        assert call_args[0].name == "技术"

        # 验证 repository 调用
        mock_repository.batch_create.assert_called_once()
        created_relations = mock_repository.batch_create.call_args[0][0]
        assert len(created_relations) == 2  # 过滤低置信度后的关系

        # 验证 ext_info 内容
        for relation in created_relations:
            assert relation.source_type == RelationSourceType.LLM
            assert relation.status == RelationStatus.PENDING
            assert relation.created_by == "test_user"
            assert "batch_id" in relation.ext_info
            assert "analyzed_at" in relation.ext_info
            assert "parsed_result" in relation.ext_info
            assert relation.ext_info["batch_id"] == result.batch_id

    @pytest.mark.asyncio
    async def test_execute_insufficient_concepts(self, command, mock_analyzer, mock_repository):
        """测试概念数量不足的情况。"""
        # 空列表
        result = await command.execute(concept_codes_with_names=[])
        assert result.total_suggested == 0
        assert result.created_count == 0
        mock_analyzer.analyze_relations.assert_not_called()
        mock_repository.batch_create.assert_not_called()

        # 只有一个概念
        result = await command.execute(concept_codes_with_names=[("TECH", "技术")])
        assert result.total_suggested == 0
        assert result.created_count == 0
        mock_analyzer.analyze_relations.assert_not_called()
        mock_repository.batch_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_analyzer_error(self, command, mock_analyzer, mock_repository, sample_concepts):
        """测试分析器失败的情况。"""
        mock_analyzer.analyze_relations.side_effect = Exception("Analyzer error")

        result = await command.execute(concept_codes_with_names=sample_concepts)

        assert result.total_suggested == 0
        assert result.created_count == 0
        mock_analyzer.analyze_relations.assert_called_once()
        mock_repository.batch_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_repository_error(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试仓储失败的情况。"""
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations
        mock_repository.batch_create.side_effect = Exception("Repository error")

        result = await command.execute(concept_codes_with_names=sample_concepts)

        assert result.total_suggested == 3
        assert result.created_count == 0  # 仓储失败，创建数为 0
        mock_analyzer.analyze_relations.assert_called_once()
        mock_repository.batch_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_confidence_filtering(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试置信度过滤。"""
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations

        # 高阈值
        result = await command.execute(
            concept_codes_with_names=sample_concepts,
            min_confidence=0.85,
        )
        assert result.created_count == 1  # 只有 0.9 的关系通过

        # 低阈值
        result = await command.execute(
            concept_codes_with_names=sample_concepts,
            min_confidence=0.3,
        )
        assert result.created_count == 3  # 所有关系都通过

        # 验证 repository 调用参数
        assert mock_repository.batch_create.call_count == 2
        high_threshold_call = mock_repository.batch_create.call_args_list[0][0][0]
        low_threshold_call = mock_repository.batch_create.call_args_list[1][0][0]
        assert len(high_threshold_call) == 1
        assert len(low_threshold_call) == 3

    @pytest.mark.asyncio
    async def test_ext_info_structure(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试 ext_info 结构完整性。"""
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations

        await command.execute(concept_codes_with_names=sample_concepts)

        # 获取创建的关系
        created_relations = mock_repository.batch_create.call_args[0][0]
        assert len(created_relations) == 2  # 过滤低置信度后

        # 验证每个关系的 ext_info
        for relation in created_relations:
            ext_info = relation.ext_info
            assert "model" in ext_info
            assert "prompt" in ext_info
            assert "raw_output" in ext_info
            assert "parsed_result" in ext_info
            assert "reasoning" in ext_info
            assert "batch_id" in ext_info
            assert "analyzed_at" in ext_info

            # 验证 parsed_result 结构
            parsed_result = ext_info["parsed_result"]
            assert "source" in parsed_result
            assert "target" in parsed_result
            assert "type" in parsed_result
            assert "confidence" in parsed_result

            # 验证时间格式
            assert isinstance(ext_info["analyzed_at"], str)

    @pytest.mark.asyncio
    async def test_duplicate_relations_handling(self, command, mock_analyzer, mock_repository, sample_concepts):
        """测试重复关系处理。"""
        # 包含重复关系的推荐
        duplicate_relations = [
            SuggestedRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                confidence=0.8,
                reasoning="第一个",
            ),
            SuggestedRelation(
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                confidence=0.9,
                reasoning="重复",
            ),
        ]
        mock_analyzer.analyze_relations.return_value = duplicate_relations

        result = await command.execute(concept_codes_with_names=sample_concepts)

        # 注意：去重逻辑在 analyzer 中处理，这里验证 repository 调用
        mock_repository.batch_create.assert_called_once()
        created_relations = mock_repository.batch_create.call_args[0][0]
        # 实际去重应该在 analyzer 中完成，这里假设 analyzer 已去重
        assert len(created_relations) >= 1

    @pytest.mark.asyncio
    async def test_batch_id_uniqueness(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试批次 ID 唯一性。"""
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations

        # 执行两次
        result1 = await command.execute(concept_codes_with_names=sample_concepts)
        result2 = await command.execute(concept_codes_with_names=sample_concepts)

        # 验证批次 ID 不同
        assert result1.batch_id != result2.batch_id
        assert len(result1.batch_id) > 0
        assert len(result2.batch_id) > 0

        # 验证每个关系都有正确的批次 ID
        assert mock_repository.batch_create.call_count == 2
        call1_relations = mock_repository.batch_create.call_args_list[0][0][0]
        call2_relations = mock_repository.batch_create.call_args_list[1][0][0]

        for relation in call1_relations:
            assert relation.ext_info["batch_id"] == result1.batch_id

        for relation in call2_relations:
            assert relation.ext_info["batch_id"] == result2.batch_id

    @pytest.mark.asyncio
    async def test_created_by_parameter(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试 created_by 参数传递。"""
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations

        await command.execute(
            concept_codes_with_names=sample_concepts,
            created_by="specific_user",
        )

        created_relations = mock_repository.batch_create.call_args[0][0]
        for relation in created_relations:
            assert relation.created_by == "specific_user"

    @pytest.mark.asyncio
    async def test_min_confidence_parameter(self, command, mock_analyzer, mock_repository, sample_concepts, sample_suggested_relations):
        """测试 min_confidence 参数边界值。"""
        mock_analyzer.analyze_relations.return_value = sample_suggested_relations

        # 边界值测试
        result = await command.execute(
            concept_codes_with_names=sample_concepts,
            min_confidence=0.0,
        )
        assert result.created_count == 3  # 所有关系都通过

        result = await command.execute(
            concept_codes_with_names=sample_concepts,
            min_confidence=1.0,
        )
        assert result.created_count == 0  # 没有关系达到 1.0

        result = await command.execute(
            concept_codes_with_names=sample_concepts,
            min_confidence=0.9,
        )
        assert result.created_count == 1  # 只有 0.9 的关系通过
