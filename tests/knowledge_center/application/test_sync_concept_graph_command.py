"""
单元测试：SyncConceptGraphCommand
Mock GraphRepository + Adapter，验证先删后建流程
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.knowledge_center.application.commands.sync_concept_graph_command import (
    SyncConceptGraphCommand,
)
from src.modules.knowledge_center.domain.dtos.concept_sync_dtos import ConceptGraphSyncDTO
from src.modules.knowledge_center.domain.dtos.graph_sync_dtos import SyncResult


class TestSyncConceptGraphCommand:
    """测试概念图谱同步命令"""

    @pytest.fixture
    def mock_graph_repo(self):
        """创建 Mock GraphRepository"""
        repo = MagicMock()
        repo.ensure_constraints = AsyncMock()
        repo.delete_all_concept_relationships = AsyncMock(return_value=100)
        repo.merge_concepts = AsyncMock(
            return_value=SyncResult(
                total=2,
                success=2,
                failed=0,
                duration_ms=100.0,
                error_details=[],
            )
        )
        return repo

    @pytest.fixture
    def mock_concept_adapter(self):
        """创建 Mock ConceptDataAdapter"""
        adapter = MagicMock()
        adapter.fetch_all_concepts_for_sync = AsyncMock()
        return adapter

    @pytest.fixture
    def command(self, mock_graph_repo, mock_concept_adapter):
        """创建测试命令实例"""
        return SyncConceptGraphCommand(
            graph_repo=mock_graph_repo,
            concept_adapter=mock_concept_adapter,
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, command, mock_graph_repo, mock_concept_adapter):
        """测试成功同步流程"""
        # Mock 概念数据
        mock_concept_adapter.fetch_all_concepts_for_sync.return_value = [
            ConceptGraphSyncDTO(
                code="BK0493",
                name="低空经济",
                stock_third_codes=["000001.SZ", "601398.SH"],
            ),
            ConceptGraphSyncDTO(
                code="BK0494",
                name="人形机器人",
                stock_third_codes=["300001.SZ"],
            ),
        ]

        result = await command.execute()

        assert result.total == 2
        assert result.success == 2
        assert result.failed == 0

        # 验证调用顺序：先删后建
        mock_graph_repo.ensure_constraints.assert_called_once()
        mock_graph_repo.delete_all_concept_relationships.assert_called_once()
        mock_graph_repo.merge_concepts.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_empty_concepts(self, command, mock_graph_repo, mock_concept_adapter):
        """测试无概念数据"""
        mock_concept_adapter.fetch_all_concepts_for_sync.return_value = []

        result = await command.execute()

        assert result.total == 0
        assert result.success == 0

        # 无数据时不应调用删除和合并
        mock_graph_repo.delete_all_concept_relationships.assert_not_called()
        mock_graph_repo.merge_concepts.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_adapter_error(self, command, mock_concept_adapter):
        """测试 Adapter 获取数据失败"""
        mock_concept_adapter.fetch_all_concepts_for_sync.side_effect = Exception("DB error")

        with pytest.raises(Exception):
            await command.execute()

    @pytest.mark.asyncio
    async def test_execute_delete_error(self, command, mock_graph_repo, mock_concept_adapter):
        """测试删除关系失败"""
        mock_concept_adapter.fetch_all_concepts_for_sync.return_value = [
            ConceptGraphSyncDTO(code="BK0493", name="低空经济", stock_third_codes=["000001.SZ"]),
        ]
        mock_graph_repo.delete_all_concept_relationships.side_effect = Exception("Neo4j error")

        with pytest.raises(Exception):
            await command.execute()

    @pytest.mark.asyncio
    async def test_execute_merge_error(self, command, mock_graph_repo, mock_concept_adapter):
        """测试合并节点失败"""
        mock_concept_adapter.fetch_all_concepts_for_sync.return_value = [
            ConceptGraphSyncDTO(code="BK0493", name="低空经济", stock_third_codes=["000001.SZ"]),
        ]
        mock_graph_repo.merge_concepts.side_effect = Exception("Neo4j error")

        with pytest.raises(Exception):
            await command.execute()

    @pytest.mark.asyncio
    async def test_execute_partial_failure(self, command, mock_graph_repo, mock_concept_adapter):
        """测试部分概念同步失败"""
        mock_concept_adapter.fetch_all_concepts_for_sync.return_value = [
            ConceptGraphSyncDTO(code="BK0493", name="低空经济", stock_third_codes=["000001.SZ"]),
            ConceptGraphSyncDTO(code="BK0494", name="人形机器人", stock_third_codes=["300001.SZ"]),
        ]

        # Mock 部分失败
        mock_graph_repo.merge_concepts.return_value = SyncResult(
            total=2,
            success=1,
            failed=1,
            duration_ms=100.0,
            error_details=["BK0494 同步失败"],
        )

        result = await command.execute()

        assert result.total == 2
        assert result.success == 1
        assert result.failed == 1
        assert len(result.error_details) == 1
