"""
单元测试：AkShareMarketDataClient
Mock akshare API，验证各 fetch_* 方法：正常返回、空数据、异常处理
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.modules.data_engineering.infrastructure.external_apis.akshare.market_data_client import (
    AkShareMarketDataClient,
)
from src.shared.domain.exceptions import AppException


class TestAkShareMarketDataClient:
    """测试 AkShare 市场数据客户端"""

    @pytest.fixture
    def client(self):
        """创建测试客户端实例"""
        return AkShareMarketDataClient(request_interval=0.05)

    @pytest.mark.asyncio
    async def test_fetch_limit_up_pool_success(self, client):
        """测试成功获取涨停池数据"""
        mock_df = pd.DataFrame(
            {
                "代码": ["000001", "601398"],
                "名称": ["平安银行", "工商银行"],
                "涨跌幅": [10.01, 10.02],
                "最新价": [15.50, 6.20],
                "成交额": [1000000.0, 2000000.0],
                "换手率": [5.5, 3.2],
                "连板数": [1, 2],
                "首次封板时间": ["09:30:00", "09:35:00"],
                "最后封板时间": ["14:50:00", "14:55:00"],
                "所属行业": ["银行", "银行"],
            }
        )

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_limit_up_pool(date(2024, 2, 15))

                assert len(result) == 2
                assert result[0].third_code == "000001.SZ"
                assert result[0].stock_name == "平安银行"
                assert result[0].consecutive_boards == 1
                assert result[1].third_code == "601398.SH"
                assert result[1].consecutive_boards == 2

    @pytest.mark.asyncio
    async def test_fetch_limit_up_pool_empty(self, client):
        """测试涨停池返回空数据"""
        mock_df = pd.DataFrame()

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_limit_up_pool(date(2024, 2, 15))

                assert result == []

    @pytest.mark.asyncio
    async def test_fetch_limit_up_pool_api_error(self, client):
        """测试涨停池 API 调用失败"""
        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", side_effect=Exception("Network error")):
                with pytest.raises(AppException) as exc_info:
                    await client.fetch_limit_up_pool(date(2024, 2, 15))

                assert exc_info.value.code == "AKSHARE_API_ERROR"

    @pytest.mark.asyncio
    async def test_fetch_broken_board_pool_success(self, client):
        """测试成功获取炸板池数据"""
        mock_df = pd.DataFrame(
            {
                "代码": ["000002", "300001"],
                "名称": ["万科A", "特锐德"],
                "涨跌幅": [8.5, 7.8],
                "最新价": [10.20, 20.50],
                "成交额": [500000.0, 800000.0],
                "换手率": [8.5, 6.2],
                "开板次数": [2, 3],
                "首次封板时间": ["10:00:00", "10:30:00"],
                "最后开板时间": ["14:00:00", "14:30:00"],
                "所属行业": ["房地产", "电气设备"],
            }
        )

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_broken_board_pool(date(2024, 2, 15))

                assert len(result) == 2
                assert result[0].third_code == "000002.SZ"
                assert result[0].open_count == 2
                assert result[1].third_code == "300001.SZ"
                assert result[1].open_count == 3

    @pytest.mark.asyncio
    async def test_fetch_broken_board_pool_empty(self, client):
        """测试炸板池返回空数据"""
        mock_df = pd.DataFrame()

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_broken_board_pool(date(2024, 2, 15))

                assert result == []

    @pytest.mark.asyncio
    async def test_fetch_previous_limit_up_success(self, client):
        """测试成功获取昨日涨停表现数据"""
        mock_df = pd.DataFrame(
            {
                "代码": ["000003", "601888"],
                "名称": ["万科B", "中国平安"],
                "涨跌幅": [5.5, -3.2],
                "最新价": [12.50, 50.80],
                "成交额": [1200000.0, 3000000.0],
                "换手率": [4.5, 2.8],
                "昨日连板数": [1, 2],
                "所属行业": ["房地产", "保险"],
            }
        )

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_previous_limit_up(date(2024, 2, 15))

                assert len(result) == 2
                assert result[0].third_code == "000003.SZ"
                assert result[0].yesterday_consecutive_boards == 1
                assert result[1].third_code == "601888.SH"
                assert result[1].yesterday_consecutive_boards == 2

    @pytest.mark.asyncio
    async def test_fetch_previous_limit_up_empty(self, client):
        """测试昨日涨停表现返回空数据"""
        mock_df = pd.DataFrame()

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_previous_limit_up(date(2024, 2, 15))

                assert result == []

    @pytest.mark.asyncio
    async def test_fetch_dragon_tiger_detail_success(self, client):
        """测试成功获取龙虎榜数据"""
        mock_df = pd.DataFrame(
            {
                "代码": ["000004", "601899"],
                "名称": ["国农科技", "紫金矿业"],
                "涨跌幅": [10.0, 8.5],
                "收盘价": [20.50, 15.80],
                "上榜原因": ["日涨幅偏离值达7%", "连续三个交易日涨幅偏离值累计达20%"],
                "龙虎榜净买额": [5000000.0, -3000000.0],
                "龙虎榜买入额": [8000000.0, 4000000.0],
                "龙虎榜卖出额": [3000000.0, 7000000.0],
                "买1席位": ["机构专用", "某证券营业部"],
                "买1金额": [3000000.0, 2000000.0],
                "买2席位": ["另一营业部", "-"],
                "买2金额": [2000000.0, 0.0],
                "买3席位": ["-", "-"],
                "买3金额": [0.0, 0.0],
                "买4席位": ["-", "-"],
                "买4金额": [0.0, 0.0],
                "买5席位": ["-", "-"],
                "买5金额": [0.0, 0.0],
                "卖1席位": ["游资席位", "机构专用"],
                "卖1金额": [1500000.0, 3500000.0],
                "卖2席位": ["-", "-"],
                "卖2金额": [0.0, 0.0],
                "卖3席位": ["-", "-"],
                "卖3金额": [0.0, 0.0],
                "卖4席位": ["-", "-"],
                "卖4金额": [0.0, 0.0],
                "卖5席位": ["-", "-"],
                "卖5金额": [0.0, 0.0],
            }
        )

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_dragon_tiger_detail(date(2024, 2, 15))

                assert len(result) == 2
                assert result[0].third_code == "000004.SZ"
                assert result[0].reason == "日涨幅偏离值达7%"
                assert len(result[0].buy_seats) == 2
                assert result[0].buy_seats[0]["seat_name"] == "机构专用"
                assert len(result[0].sell_seats) == 1

    @pytest.mark.asyncio
    async def test_fetch_dragon_tiger_detail_empty(self, client):
        """测试龙虎榜返回空数据"""
        mock_df = pd.DataFrame()

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_dragon_tiger_detail(date(2024, 2, 15))

                assert result == []

    @pytest.mark.asyncio
    async def test_fetch_sector_capital_flow_success(self, client):
        """测试成功获取板块资金流向数据"""
        mock_df = pd.DataFrame(
            {
                "名称": ["人工智能", "低空经济", "新能源"],
                "今日主力净流入-净额": [50000000.0, -20000000.0, 30000000.0],
                "今日主力净流入-流入额": [100000000.0, 30000000.0, 80000000.0],
                "今日主力净流入-流出额": [50000000.0, 50000000.0, 50000000.0],
                "今日涨跌幅": [3.5, -1.2, 2.8],
            }
        )

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_sector_capital_flow("概念资金流")

                assert len(result) == 3
                assert result[0].sector_name == "人工智能"
                assert result[0].sector_type == "概念资金流"
                assert result[0].net_amount == 50000000.0
                assert result[1].sector_name == "低空经济"

    @pytest.mark.asyncio
    async def test_fetch_sector_capital_flow_empty(self, client):
        """测试板块资金流向返回空数据"""
        mock_df = pd.DataFrame()

        with patch("builtins.__import__") as mock_import:
            mock_ak = MagicMock()
            mock_import.return_value = mock_ak
            with patch.object(client, "_run_in_executor", return_value=mock_df):
                result = await client.fetch_sector_capital_flow("概念资金流")

                assert result == []

    @pytest.mark.asyncio
    async def test_import_error(self, client):
        """测试 akshare 库导入失败"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'akshare'")):
            with pytest.raises(AppException) as exc_info:
                await client.fetch_limit_up_pool(date(2024, 2, 15))

            assert exc_info.value.code == "AKSHARE_IMPORT_ERROR"
