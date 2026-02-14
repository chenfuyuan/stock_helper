"""
单元测试：SyncConceptDataCmd
Mock Provider + Repository，验证同步流程和错误隔离
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.data_engineering.application.commands.sync_concept_data_cmd import (
    SyncConceptDataCmd,
)
from src.modules.data_engineering.domain.dtos.concept_dtos import (
    ConceptConstituentDTO,
    ConceptInfoDTO,
)
from src.modules.data_engineering.domain.model.concept import Concept, ConceptStock


class TestSyncConceptDataCmd:
    """测试概念数据同步命令"""

    @pytest.fixture
    def mock_provider(self):
        """创建 Mock Provider"""
        provider = MagicMock()
        provider.fetch_concept_list = AsyncMock()
        provider.fetch_concept_constituents = AsyncMock()
        return provider

    @pytest.fixture
    def mock_repository(self):
        """创建 Mock Repository"""
        repo = MagicMock()
        repo.upsert_concepts = AsyncMock(return_value=2)
        repo.replace_all_concept_stocks = AsyncMock(return_value=5)
        return repo

    @pytest.fixture
    def command(self, mock_provider, mock_repository):
        """创建测试命令实例"""
        return SyncConceptDataCmd(
            concept_provider=mock_provider,
            concept_repo=mock_repository,
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, command, mock_provider, mock_repository):
        """测试成功同步流程"""
        # Mock 概念列表
        mock_provider.fetch_concept_list.return_value = [
            ConceptInfoDTO(code="BK0493", name="低空经济"),
            ConceptInfoDTO(code="BK0494", name="人形机器人"),
        ]

        # Mock 成份股
        mock_provider.fetch_concept_constituents.side_effect = [
            [
                ConceptConstituentDTO(stock_code="000001.SZ", stock_name="平安银行"),
                ConceptConstituentDTO(stock_code="601398.SH", stock_name="工商银行"),
            ],
            [
                ConceptConstituentDTO(stock_code="300001.SZ", stock_name="特锐德"),
            ],
        ]

        result = await command.execute()

        assert result.total_concepts == 2
        assert result.success_concepts == 2
        assert result.failed_concepts == 0
        assert result.total_stocks == 3

        # 验证调用
        mock_provider.fetch_concept_list.assert_called_once()
        assert mock_provider.fetch_concept_constituents.call_count == 2
        mock_repository.upsert_concepts.assert_called_once()
        mock_repository.replace_all_concept_stocks.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_empty_concepts(self, command, mock_provider):
        """测试无概念数据"""
        mock_provider.fetch_concept_list.return_value = []

        result = await command.execute()

        assert result.total_concepts == 0
        assert result.success_concepts == 0
        assert result.total_stocks == 0

    @pytest.mark.asyncio
    async def test_execute_with_constituent_error(self, command, mock_provider, mock_repository):
        """测试成份股获取失败时的错误隔离"""
        mock_provider.fetch_concept_list.return_value = [
            ConceptInfoDTO(code="BK0493", name="低空经济"),
            ConceptInfoDTO(code="BK0494", name="人形机器人"),
        ]

        # 第一个概念成功，第二个失败
        mock_provider.fetch_concept_constituents.side_effect = [
            [ConceptConstituentDTO(stock_code="000001.SZ", stock_name="平安银行")],
            Exception("Network error"),
        ]

        result = await command.execute()

        assert result.total_concepts == 2
        assert result.success_concepts == 1  # 仅第一个成功
        assert result.failed_concepts == 1
        assert result.total_stocks == 1

        # 仍然应该调用 upsert 和 replace
        mock_repository.upsert_concepts.assert_called_once()
        mock_repository.replace_all_concept_stocks.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_provider_error(self, command, mock_provider):
        """测试 Provider 获取概念列表失败"""
        mock_provider.fetch_concept_list.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await command.execute()

    @pytest.mark.asyncio
    async def test_execute_repository_error(self, command, mock_provider, mock_repository):
        """测试 Repository 写入失败"""
        mock_provider.fetch_concept_list.return_value = [
            ConceptInfoDTO(code="BK0493", name="低空经济"),
        ]
        mock_provider.fetch_concept_constituents.return_value = [
            ConceptConstituentDTO(stock_code="000001.SZ", stock_name="平安银行"),
        ]
        mock_repository.upsert_concepts.side_effect = Exception("DB error")

        with pytest.raises(Exception):
            await command.execute()

    @pytest.mark.asyncio
    async def test_execute_with_empty_constituents(self, command, mock_provider, mock_repository):
        """测试某些概念无成份股"""
        mock_provider.fetch_concept_list.return_value = [
            ConceptInfoDTO(code="BK0493", name="低空经济"),
        ]
        mock_provider.fetch_concept_constituents.return_value = []

        result = await command.execute()

        assert result.total_concepts == 1
        assert result.success_concepts == 1
        assert result.total_stocks == 0

        # 仍然应该调用 upsert
        mock_repository.upsert_concepts.assert_called_once()
        mock_repository.replace_all_concept_stocks.assert_called_once()
