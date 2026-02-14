"""
单元测试：ConceptDataAdapter
Mock IConceptRepository，验证 DTO 转换
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.data_engineering.domain.dtos.concept_dtos import ConceptWithStocksDTO
from src.modules.data_engineering.domain.model.concept import Concept, ConceptStock
from src.modules.knowledge_center.infrastructure.adapters.concept_data_adapter import (
    ConceptDataAdapter,
)


class TestConceptDataAdapter:
    """测试概念数据适配器"""

    @pytest.fixture
    def mock_concept_repo(self):
        """创建 Mock ConceptRepository"""
        repo = MagicMock()
        repo.get_all_concepts_with_stocks = AsyncMock()
        return repo

    @pytest.fixture
    def adapter(self, mock_concept_repo):
        """创建测试适配器实例"""
        return ConceptDataAdapter(concept_repo=mock_concept_repo)

    @pytest.mark.asyncio
    async def test_fetch_all_concepts_for_sync_success(self, adapter, mock_concept_repo):
        """测试成功获取并转换概念数据"""
        # Mock DE 模块返回的数据
        mock_concept_repo.get_all_concepts_with_stocks.return_value = [
            ConceptWithStocksDTO(
                code="BK0493",
                name="低空经济",
                stocks=[
                    ConceptStock(concept_code="BK0493", third_code="000001.SZ", stock_name="平安银行"),
                    ConceptStock(concept_code="BK0493", third_code="601398.SH", stock_name="工商银行"),
                ],
            ),
            ConceptWithStocksDTO(
                code="BK0494",
                name="人形机器人",
                stocks=[
                    ConceptStock(concept_code="BK0494", third_code="300001.SZ", stock_name="特锐德"),
                ],
            ),
        ]

        result = await adapter.fetch_all_concepts_for_sync()

        assert len(result) == 2
        assert result[0].code == "BK0493"
        assert result[0].name == "低空经济"
        assert result[0].stock_third_codes == ["000001.SZ", "601398.SH"]
        assert result[1].code == "BK0494"
        assert result[1].name == "人形机器人"
        assert result[1].stock_third_codes == ["300001.SZ"]

        mock_concept_repo.get_all_concepts_with_stocks.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_all_concepts_for_sync_empty(self, adapter, mock_concept_repo):
        """测试无概念数据"""
        mock_concept_repo.get_all_concepts_with_stocks.return_value = []

        result = await adapter.fetch_all_concepts_for_sync()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_all_concepts_for_sync_no_stocks(self, adapter, mock_concept_repo):
        """测试概念无成份股"""
        mock_concept_repo.get_all_concepts_with_stocks.return_value = [
            ConceptWithStocksDTO(
                code="BK0493",
                name="低空经济",
                stocks=[],
            ),
        ]

        result = await adapter.fetch_all_concepts_for_sync()

        assert len(result) == 1
        assert result[0].code == "BK0493"
        assert result[0].stock_third_codes == []

    @pytest.mark.asyncio
    async def test_fetch_all_concepts_for_sync_error(self, adapter, mock_concept_repo):
        """测试 Repository 调用失败"""
        mock_concept_repo.get_all_concepts_with_stocks.side_effect = Exception("DB error")

        with pytest.raises(Exception):
            await adapter.fetch_all_concepts_for_sync()
