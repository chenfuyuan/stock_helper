"""
概念关系同步命令单元测试。

测试 SyncConceptRelationsCmd 的流程编排，使用 mock Repository 和 GraphRepository。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.knowledge_center.application.commands.sync_concept_relations_command import (
    SyncConceptRelationsCmd,
    SyncConceptRelationsResult,
)
from src.modules.knowledge_center.domain.dtos.concept_relation_sync_dtos import (
    ConceptRelationSyncDTO,
)
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult
from src.modules.knowledge_center.domain.model.concept_relation import ConceptRelation
from src.modules.knowledge_center.domain.model.enums import (
    RelationSourceType,
    RelationStatus,
)


class TestSyncConceptRelationsCmd:
    """概念关系同步命令测试类。"""

    @pytest.fixture
    def mock_pg_repository(self):
        """Mock PostgreSQL 概念关系仓储。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_graph_repository(self):
        """Mock Neo4j 图谱仓储。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def command(self, mock_pg_repository, mock_graph_repository):
        """创建命令实例。"""
        return SyncConceptRelationsCmd(
            pg_repository=mock_pg_repository,
            graph_repository=mock_graph_repository,
        )

    @pytest.fixture
    def sample_confirmed_relations(self):
        """示例已确认的关系列表。"""
        return [
            ConceptRelation(
                id=1,
                source_concept_code="TECH",
                target_concept_code="AI",
                relation_type="IS_UPSTREAM_OF",
                source_type=RelationSourceType.MANUAL,
                status=RelationStatus.CONFIRMED,
                confidence=1.0,
                ext_info={"note": "手动创建"},
            ),
            ConceptRelation(
                id=2,
                source_concept_code="CHIP",
                target_concept_code="AI",
                relation_type="IS_PART_OF",
                source_type=RelationSourceType.LLM,
                status=RelationStatus.CONFIRMED,
                confidence=0.8,
                ext_info={"model": "gpt-4"},
            ),
        ]

    @pytest.fixture
    def sample_sync_result(self):
        """示例同步结果。"""
        return SyncResult(
            total=2,
            success=2,
            failed=0,
            duration_ms=100.0,
            error_details=[],
        )

    @pytest.mark.asyncio
    async def test_execute_incremental_success(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations, sample_sync_result):
        """测试增量同步成功。"""
        # Mock 返回
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        mock_graph_repository.merge_concept_relations.return_value = sample_sync_result

        # 执行命令
        result = await command.execute(mode="incremental", batch_size=100)

        # 验证结果
        assert isinstance(result, SyncConceptRelationsResult)
        assert result.mode == "incremental"
        assert result.total_relations == 2
        assert result.deleted_count == 0  # 增量模式不删除
        assert result.sync_success == 2
        assert result.sync_failed == 0
        assert result.duration_ms == 100.0

        # 验证调用
        mock_pg_repository.get_all_confirmed.assert_called_once()
        mock_graph_repository.delete_all_concept_inter_relationships.assert_not_called()  # 增量模式不删除
        mock_graph_repository.merge_concept_relations.assert_called_once()

        # 验证同步参数
        sync_call = mock_graph_repository.merge_concept_relations.call_args
        assert sync_call.kwargs["batch_size"] == 100
        
        # 验证同步数据
        sync_data = sync_call.kwargs["relations"]
        assert len(sync_data) == 2
        assert all(isinstance(r, ConceptRelationSyncDTO) for r in sync_data)
        assert sync_data[0].pg_id == 1
        assert sync_data[0].source_concept_code == "TECH"
        assert sync_data[0].target_concept_code == "AI"
        assert sync_data[0].relation_type == "IS_UPSTREAM_OF"
        assert sync_data[0].source_type == "MANUAL"
        assert sync_data[0].confidence == 1.0

    @pytest.mark.asyncio
    async def test_execute_rebuild_success(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations, sample_sync_result):
        """测试全量重建成功。"""
        # Mock 返回
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        mock_graph_repository.delete_all_concept_inter_relationships.return_value = 5  # 删除了 5 条旧关系
        mock_graph_repository.merge_concept_relations.return_value = sample_sync_result

        # 执行命令
        result = await command.execute(mode="rebuild", batch_size=50)

        # 验证结果
        assert result.mode == "rebuild"
        assert result.total_relations == 2
        assert result.deleted_count == 5  # 重建模式删除旧关系
        assert result.sync_success == 2
        assert result.sync_failed == 0

        # 验证调用顺序
        mock_graph_repository.delete_all_concept_inter_relationships.assert_called_once()
        mock_pg_repository.get_all_confirmed.assert_called_once()
        mock_graph_repository.merge_concept_relations.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_confirmed_relations(self, command, mock_pg_repository, mock_graph_repository):
        """测试没有已确认关系的情况。"""
        mock_pg_repository.get_all_confirmed.return_value = []

        result = await command.execute(mode="incremental")

        assert result.total_relations == 0
        assert result.sync_success == 0
        assert result.sync_failed == 0

        mock_pg_repository.get_all_confirmed.assert_called_once()
        mock_graph_repository.merge_concept_relations.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_invalid_mode(self, command, mock_pg_repository, mock_graph_repository):
        """测试无效同步模式。"""
        with pytest.raises(ValueError, match="无效的同步模式"):
            await command.execute(mode="invalid_mode")

        mock_pg_repository.get_all_confirmed.assert_not_called()
        mock_graph_repository.merge_concept_relations.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_pg_repository_error(self, command, mock_pg_repository, mock_graph_repository):
        """测试 PostgreSQL 仓储错误。"""
        mock_pg_repository.get_all_confirmed.side_effect = Exception("PG error")

        with pytest.raises(Exception, match="PG error"):
            await command.execute(mode="incremental")

        mock_pg_repository.get_all_confirmed.assert_called_once()
        mock_graph_repository.merge_concept_relations.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_graph_repository_error(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations):
        """测试 Neo4j 仓储错误。"""
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        mock_graph_repository.merge_concept_relations.side_effect = Exception("Neo4j error")

        with pytest.raises(Exception, match="Neo4j error"):
            await command.execute(mode="incremental")

        mock_pg_repository.get_all_confirmed.assert_called_once()
        mock_graph_repository.merge_concept_relations.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_rebuild_delete_error(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations):
        """测试重建模式删除错误。"""
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        mock_graph_repository.delete_all_concept_inter_relationships.side_effect = Exception("Delete error")

        with pytest.raises(Exception, match="Delete error"):
            await command.execute(mode="rebuild")

        mock_graph_repository.delete_all_concept_inter_relationships.assert_called_once()
        mock_pg_repository.get_all_confirmed.assert_not_called()  # 删除失败，不继续
        mock_graph_repository.merge_concept_relations.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_size_parameter(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations, sample_sync_result):
        """测试批次大小参数。"""
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        mock_graph_repository.merge_concept_relations.return_value = sample_sync_result

        # 测试自定义批次大小
        await command.execute(mode="incremental", batch_size=200)

        sync_call = mock_graph_repository.merge_concept_relations.call_args
        assert sync_call.kwargs["batch_size"] == 200

        # 测试默认批次大小
        await command.execute(mode="incremental")

        sync_call = mock_graph_repository.merge_concept_relations.call_args
        assert sync_call.kwargs["batch_size"] == 500  # 默认值

    @pytest.mark.asyncio
    async def test_sync_dto_conversion(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations, sample_sync_result):
        """测试同步 DTO 转换。"""
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        mock_graph_repository.merge_concept_relations.return_value = sample_sync_result

        await command.execute(mode="incremental")

        sync_call = mock_graph_repository.merge_concept_relations.call_args
        sync_data = sync_call.kwargs["relations"]

        # 验证 DTO 转换
        assert len(sync_data) == 2
        
        # 验证第一个 DTO
        dto1 = sync_data[0]
        assert isinstance(dto1, ConceptRelationSyncDTO)
        assert dto1.pg_id == 1
        assert dto1.source_concept_code == "TECH"
        assert dto1.target_concept_code == "AI"
        assert dto1.relation_type == "IS_UPSTREAM_OF"
        assert dto1.source_type == "MANUAL"
        assert dto1.confidence == 1.0

        # 验证第二个 DTO
        dto2 = sync_data[1]
        assert dto2.pg_id == 2
        assert dto2.source_concept_code == "CHIP"
        assert dto2.target_concept_code == "AI"
        assert dto2.relation_type == "IS_PART_OF"
        assert dto2.source_type == "LLM"
        assert dto2.confidence == 0.8

    @pytest.mark.asyncio
    async def test_sync_result_mapping(self, command, mock_pg_repository, mock_graph_repository, sample_confirmed_relations):
        """测试同步结果映射。"""
        mock_pg_repository.get_all_confirmed.return_value = sample_confirmed_relations
        
        # 模拟部分失败的同步结果
        sync_result = SyncResult(
            total=2,
            success=1,
            failed=1,
            duration_ms=150.5,
            error_details=["Error message"],
        )
        mock_graph_repository.merge_concept_relations.return_value = sync_result

        result = await command.execute(mode="incremental")

        assert result.sync_success == 1
        assert result.sync_failed == 1
        assert result.duration_ms == 150.5

    @pytest.mark.asyncio
    async def test_empty_confirmed_relations_with_rebuild(self, command, mock_pg_repository, mock_graph_repository):
        """测试重建模式下没有已确认关系的情况。"""
        mock_pg_repository.get_all_confirmed.return_value = []
        mock_graph_repository.delete_all_concept_inter_relationships.return_value = 3

        result = await command.execute(mode="rebuild")

        assert result.total_relations == 0
        assert result.deleted_count == 3  # 仍然执行删除
        assert result.sync_success == 0
        assert result.sync_failed == 0

        mock_graph_repository.delete_all_concept_inter_relationships.assert_called_once()
        mock_graph_repository.merge_concept_relations.assert_not_called()

    @pytest.mark.asyncio
    async def test_large_batch_handling(self, command, mock_pg_repository, mock_graph_repository, sample_sync_result):
        """测试大批量数据处理。"""
        # 创建大量关系
        large_relations = []
        for i in range(1000):
            relation = ConceptRelation(
                id=i + 1,
                source_concept_code=f"CONCEPT_{i}",
                target_concept_code=f"CONCEPT_{i+1}",
                relation_type="IS_UPSTREAM_OF",
                source_type=RelationSourceType.MANUAL,
                status=RelationStatus.CONFIRMED,
                confidence=1.0,
                ext_info={},
            )
            large_relations.append(relation)

        mock_pg_repository.get_all_confirmed.return_value = large_relations
        mock_graph_repository.merge_concept_relations.return_value = SyncResult(
            total=1000,
            success=1000,
            failed=0,
            duration_ms=1000.0,
            error_details=[],
        )

        result = await command.execute(mode="incremental", batch_size=100)

        assert result.total_relations == 1000
        assert result.sync_success == 1000
        assert result.sync_failed == 0

        # 验证批次大小传递
        sync_call = mock_graph_repository.merge_concept_relations.call_args
        assert sync_call.kwargs["batch_size"] == 100

        # 验证数据量
        sync_data = sync_call.kwargs["relations"]
        assert len(sync_data) == 1000
