"""
单元测试：AkShareConceptClient
Mock akshare API，验证 DTO 转换和异常处理
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.modules.data_engineering.infrastructure.external_apis.akshare.client import (
    AkShareConceptClient,
)
from src.shared.domain.exceptions import AppException


class TestAkShareConceptClient:
    """测试 AkShare 概念数据客户端"""

    @pytest.fixture
    def client(self):
        """创建测试客户端实例"""
        return AkShareConceptClient(request_interval=0.1)

    @pytest.mark.asyncio
    async def test_fetch_concept_list_success(self, client):
        """测试成功获取概念板块列表"""
        # Mock akshare 返回数据
        mock_df = pd.DataFrame({
            "板块代码": ["BK0493", "BK0494"],
            "板块名称": ["低空经济", "人形机器人"],
        })

        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_name_em = MagicMock(return_value=mock_df)

            result = await client.fetch_concept_list()

            assert len(result) == 2
            assert result[0].code == "BK0493"
            assert result[0].name == "低空经济"
            assert result[1].code == "BK0494"
            assert result[1].name == "人形机器人"

    @pytest.mark.asyncio
    async def test_fetch_concept_list_empty(self, client):
        """测试返回空列表"""
        mock_df = pd.DataFrame()

        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_name_em = MagicMock(return_value=mock_df)

            result = await client.fetch_concept_list()

            assert result == []

    @pytest.mark.asyncio
    async def test_fetch_concept_list_api_error(self, client):
        """测试 API 调用失败"""
        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_name_em = MagicMock(
                side_effect=Exception("Network error")
            )

            with pytest.raises(AppException) as exc_info:
                await client.fetch_concept_list()

            assert exc_info.value.code == "AKSHARE_API_ERROR"

    @pytest.mark.asyncio
    async def test_fetch_concept_constituents_success(self, client):
        """测试成功获取概念成份股"""
        mock_df = pd.DataFrame({
            "代码": ["000001", "601398", "688001"],
            "名称": ["平安银行", "工商银行", "华兴源创"],
        })

        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_cons_em = MagicMock(return_value=mock_df)

            result = await client.fetch_concept_constituents("低空经济")

            assert len(result) == 3
            assert result[0].stock_code == "000001.SZ"
            assert result[0].stock_name == "平安银行"
            assert result[1].stock_code == "601398.SH"
            assert result[1].stock_name == "工商银行"
            assert result[2].stock_code == "688001.SH"
            assert result[2].stock_name == "华兴源创"

    @pytest.mark.asyncio
    async def test_fetch_concept_constituents_with_invalid_code(self, client):
        """测试成份股中包含无效代码"""
        mock_df = pd.DataFrame({
            "代码": ["000001", "999999"],  # 999999 无法识别
            "名称": ["平安银行", "无效股票"],
        })

        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_cons_em = MagicMock(return_value=mock_df)

            result = await client.fetch_concept_constituents("低空经济")

            # 无效代码应被过滤
            assert len(result) == 1
            assert result[0].stock_code == "000001.SZ"

    @pytest.mark.asyncio
    async def test_fetch_concept_constituents_empty(self, client):
        """测试返回空成份股"""
        mock_df = pd.DataFrame()

        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_cons_em = MagicMock(return_value=mock_df)

            result = await client.fetch_concept_constituents("低空经济")

            assert result == []

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """测试限速机制"""
        import time

        mock_df = pd.DataFrame({
            "板块代码": ["BK0493"],
            "板块名称": ["低空经济"],
        })

        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare") as mock_ak:
            mock_ak.stock_board_concept_name_em = MagicMock(return_value=mock_df)

            start = time.time()
            await client.fetch_concept_list()
            await client.fetch_concept_list()
            elapsed = time.time() - start

            # 两次调用至少间隔 request_interval (0.1s)
            assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_import_error(self, client):
        """测试 akshare 库导入失败"""
        with patch("src.modules.data_engineering.infrastructure.external_apis.akshare.client.akshare", None):
            with pytest.raises(AppException) as exc_info:
                await client.fetch_concept_list()

            assert exc_info.value.code == "AKSHARE_IMPORT_ERROR"
