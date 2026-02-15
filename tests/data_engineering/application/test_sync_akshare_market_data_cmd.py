"""
单元测试：SyncAkShareMarketDataCmd
Mock 全部 Provider + Repository，验证：正常全量同步、部分失败异常隔离、幂等行为
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.data_engineering.domain.dtos.capital_flow_dtos import SectorCapitalFlowDTO
from src.modules.data_engineering.domain.dtos.dragon_tiger_dtos import DragonTigerDetailDTO
from src.modules.data_engineering.domain.dtos.market_sentiment_dtos import (
    BrokenBoardDTO,
    LimitUpPoolDTO,
    PreviousLimitUpDTO,
)


class TestSyncAkShareMarketDataCmd:
    """测试 AkShare 市场数据同步命令"""

    @pytest.fixture
    def mock_sentiment_provider(self):
        """创建 Mock 市场情绪 Provider"""
        provider = MagicMock()
        provider.fetch_limit_up_pool = AsyncMock()
        provider.fetch_broken_board_pool = AsyncMock()
        provider.fetch_previous_limit_up = AsyncMock()
        return provider

    @pytest.fixture
    def mock_dragon_tiger_provider(self):
        """创建 Mock 龙虎榜 Provider"""
        provider = MagicMock()
        provider.fetch_dragon_tiger_detail = AsyncMock()
        return provider

    @pytest.fixture
    def mock_capital_flow_provider(self):
        """创建 Mock 资金流向 Provider"""
        provider = MagicMock()
        provider.fetch_sector_capital_flow = AsyncMock()
        return provider

    @pytest.fixture
    def mock_repositories(self):
        """创建 Mock Repositories"""
        return {
            "limit_up_pool": MagicMock(save_all=AsyncMock(return_value=10)),
            "broken_board": MagicMock(save_all=AsyncMock(return_value=5)),
            "previous_limit_up": MagicMock(save_all=AsyncMock(return_value=8)),
            "dragon_tiger": MagicMock(save_all=AsyncMock(return_value=3)),
            "sector_capital_flow": MagicMock(save_all=AsyncMock(return_value=20)),
        }

    @pytest.fixture
    def command(
        self,
        mock_sentiment_provider,
        mock_dragon_tiger_provider,
        mock_capital_flow_provider,
        mock_repositories,
    ):
        """创建测试命令实例"""
        from src.modules.data_engineering.application.commands.sync_akshare_market_data_cmd import (
            SyncAkShareMarketDataCmd,
        )

        return SyncAkShareMarketDataCmd(
            sentiment_provider=mock_sentiment_provider,
            dragon_tiger_provider=mock_dragon_tiger_provider,
            capital_flow_provider=mock_capital_flow_provider,
            limit_up_pool_repo=mock_repositories["limit_up_pool"],
            broken_board_repo=mock_repositories["broken_board"],
            previous_limit_up_repo=mock_repositories["previous_limit_up"],
            dragon_tiger_repo=mock_repositories["dragon_tiger"],
            sector_capital_flow_repo=mock_repositories["sector_capital_flow"],
        )

    @pytest.mark.asyncio
    async def test_execute_success_full_sync(
        self,
        command,
        mock_sentiment_provider,
        mock_dragon_tiger_provider,
        mock_capital_flow_provider,
        mock_repositories,
    ):
        """测试正常全量同步"""
        test_date = date(2024, 2, 15)

        # Mock 市场情绪数据
        mock_sentiment_provider.fetch_limit_up_pool.return_value = [
            LimitUpPoolDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                amount=100000.0,
                turnover_rate=5.5,
                consecutive_boards=1,
                first_limit_up_time="09:30:00",
                last_limit_up_time="14:50:00",
                industry="银行",
            )
        ]
        mock_sentiment_provider.fetch_broken_board_pool.return_value = [
            BrokenBoardDTO(
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=8.5,
                close=10.2,
                amount=50000.0,
                turnover_rate=8.5,
                open_count=2,
                first_limit_up_time="10:00:00",
                last_open_time="14:00:00",
                industry="房地产",
            )
        ]
        mock_sentiment_provider.fetch_previous_limit_up.return_value = [
            PreviousLimitUpDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=5.5,
                close=12.5,
                amount=120000.0,
                turnover_rate=4.5,
                yesterday_consecutive_boards=1,
                industry="房地产",
            )
        ]

        # Mock 龙虎榜数据
        mock_dragon_tiger_provider.fetch_dragon_tiger_detail.return_value = [
            DragonTigerDetailDTO(
                third_code="000004.SZ",
                stock_name="国农科技",
                pct_chg=10.0,
                close=20.5,
                reason="日涨幅偏离值达7%",
                net_amount=5000000.0,
                buy_amount=8000000.0,
                sell_amount=3000000.0,
                buy_seats=[{"seat_name": "机构专用", "buy_amount": 3000000.0}],
                sell_seats=[{"seat_name": "游资席位", "sell_amount": 1500000.0}],
            )
        ]

        # Mock 资金流向数据
        mock_capital_flow_provider.fetch_sector_capital_flow.return_value = [
            SectorCapitalFlowDTO(
                sector_name="人工智能",
                sector_type="概念资金流",
                net_amount=50000000.0,
                inflow_amount=100000000.0,
                outflow_amount=50000000.0,
                pct_chg=3.5,
            )
        ]

        result = await command.execute(test_date)

        assert result.trade_date == test_date
        assert result.limit_up_pool_count == 10
        assert result.broken_board_count == 5
        assert result.previous_limit_up_count == 8
        assert result.dragon_tiger_count == 3
        assert result.sector_capital_flow_count == 20
        assert len(result.errors) == 0

        # 验证所有 Provider 都被调用
        mock_sentiment_provider.fetch_limit_up_pool.assert_called_once_with(test_date)
        mock_sentiment_provider.fetch_broken_board_pool.assert_called_once_with(test_date)
        mock_sentiment_provider.fetch_previous_limit_up.assert_called_once_with(test_date)
        mock_dragon_tiger_provider.fetch_dragon_tiger_detail.assert_called_once_with(test_date)
        mock_capital_flow_provider.fetch_sector_capital_flow.assert_called_once()

        # 验证所有 Repository 都被调用
        mock_repositories["limit_up_pool"].save_all.assert_called_once()
        mock_repositories["broken_board"].save_all.assert_called_once()
        mock_repositories["previous_limit_up"].save_all.assert_called_once()
        mock_repositories["dragon_tiger"].save_all.assert_called_once()
        mock_repositories["sector_capital_flow"].save_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_partial_failure(
        self,
        command,
        mock_sentiment_provider,
        mock_dragon_tiger_provider,
        mock_capital_flow_provider,
    ):
        """测试部分失败异常隔离"""
        test_date = date(2024, 2, 15)

        # 涨停池成功
        mock_sentiment_provider.fetch_limit_up_pool.return_value = [
            LimitUpPoolDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                amount=100000.0,
                turnover_rate=5.5,
                consecutive_boards=1,
                first_limit_up_time="09:30:00",
                last_limit_up_time="14:50:00",
                industry="银行",
            )
        ]

        # 炸板池失败
        mock_sentiment_provider.fetch_broken_board_pool.side_effect = Exception("API error")

        # 昨日涨停表现成功
        mock_sentiment_provider.fetch_previous_limit_up.return_value = [
            PreviousLimitUpDTO(
                third_code="000003.SZ",
                stock_name="万科B",
                pct_chg=5.5,
                close=12.5,
                amount=120000.0,
                turnover_rate=4.5,
                yesterday_consecutive_boards=1,
                industry="房地产",
            )
        ]

        # 龙虎榜失败
        mock_dragon_tiger_provider.fetch_dragon_tiger_detail.side_effect = Exception(
            "Network error"
        )

        # 资金流向成功
        mock_capital_flow_provider.fetch_sector_capital_flow.return_value = [
            SectorCapitalFlowDTO(
                sector_name="人工智能",
                sector_type="概念资金流",
                net_amount=50000000.0,
                inflow_amount=100000000.0,
                outflow_amount=50000000.0,
                pct_chg=3.5,
            )
        ]

        result = await command.execute(test_date)

        # 成功的应该有数据
        assert result.limit_up_pool_count == 10
        assert result.previous_limit_up_count == 8
        assert result.sector_capital_flow_count == 20

        # 失败的应该为 0
        assert result.broken_board_count == 0
        assert result.dragon_tiger_count == 0

        # 应该有 2 个错误
        assert len(result.errors) == 2
        assert any("炸板池" in err for err in result.errors)
        assert any("龙虎榜" in err for err in result.errors)

    @pytest.mark.asyncio
    async def test_execute_with_empty_data(
        self,
        command,
        mock_sentiment_provider,
        mock_dragon_tiger_provider,
        mock_capital_flow_provider,
    ):
        """测试所有数据源返回空数据"""
        test_date = date(2024, 2, 15)

        # 所有 Provider 返回空列表
        mock_sentiment_provider.fetch_limit_up_pool.return_value = []
        mock_sentiment_provider.fetch_broken_board_pool.return_value = []
        mock_sentiment_provider.fetch_previous_limit_up.return_value = []
        mock_dragon_tiger_provider.fetch_dragon_tiger_detail.return_value = []
        mock_capital_flow_provider.fetch_sector_capital_flow.return_value = []

        result = await command.execute(test_date)

        assert result.limit_up_pool_count == 0
        assert result.broken_board_count == 0
        assert result.previous_limit_up_count == 0
        assert result.dragon_tiger_count == 0
        assert result.sector_capital_flow_count == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_idempotent(
        self,
        command,
        mock_sentiment_provider,
        mock_dragon_tiger_provider,
        mock_capital_flow_provider,
        mock_repositories,
    ):
        """测试幂等行为（多次调用相同日期）"""
        test_date = date(2024, 2, 15)

        # Mock 数据
        mock_sentiment_provider.fetch_limit_up_pool.return_value = [
            LimitUpPoolDTO(
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.0,
                close=15.5,
                amount=100000.0,
                turnover_rate=5.5,
                consecutive_boards=1,
                first_limit_up_time="09:30:00",
                last_limit_up_time="14:50:00",
                industry="银行",
            )
        ]
        mock_sentiment_provider.fetch_broken_board_pool.return_value = []
        mock_sentiment_provider.fetch_previous_limit_up.return_value = []
        mock_dragon_tiger_provider.fetch_dragon_tiger_detail.return_value = []
        mock_capital_flow_provider.fetch_sector_capital_flow.return_value = []

        # 执行两次
        result1 = await command.execute(test_date)
        result2 = await command.execute(test_date)

        # 两次结果应该一致
        assert result1.limit_up_pool_count == result2.limit_up_pool_count
        assert len(result1.errors) == len(result2.errors)

        # Repository 应该被调用两次（UPSERT 保证幂等）
        assert mock_repositories["limit_up_pool"].save_all.call_count == 2
