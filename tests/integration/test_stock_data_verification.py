import pytest

from src.modules.market_data.application.use_cases.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_daily_repository import (
    StockDailyRepositoryImpl,
)
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_repository import (
    StockRepositoryImpl,
)


@pytest.mark.asyncio
class TestStockFetchIntegration:
    """
    针对特定股票 (000001.SZ) 的集成测试，验证能否从数据库中正确获取信息
    """

    async def test_fetch_pingan_bank_info(self, db_session):
        # 1. 初始化 Repository 和 Use Case
        # 注意：这里使用的是真实的数据库会话，但由于 conftest.py 中的 db_session fixture
        # 使用了事务回滚模式，所以这里如果是查询已有数据是没问题的。
        stock_repo = StockRepositoryImpl(db_session)
        daily_repo = StockDailyRepositoryImpl(db_session)
        use_case = GetStockBasicInfoUseCase(stock_repo, daily_repo)

        # 2. 执行查询 (000001)
        symbol = "000001"
        result = await use_case.execute(symbol)

        # 3. 验证结果 (基于数据库中已有的真实数据)
        # 如果数据库中没有该数据，测试会失败，这正是集成测试验证真实环境的目的
        assert result is not None, f"数据库中未找到代码为 {symbol} 的股票信息"
        assert result.info.name == "平安银行"
        assert result.info.third_code == "000001.SZ"

        # 4. 验证行情数据 (如果存在)
        if result.daily:
            print(
                f"\n[Verified] {symbol} latest price: {result.daily.close} at {result.daily.trade_date}"
            )
            assert result.daily.close > 0
            assert result.daily.trade_date is not None
        else:
            print(
                f"\n[Warning] {symbol} info found but daily data is missing."
            )

    async def test_fetch_by_third_code_directly(self, db_session):
        # 直接验证 Repository 层通过 third_code 获取
        stock_repo = StockRepositoryImpl(db_session)
        third_code = "000001.SZ"

        stock = await stock_repo.get_by_third_code(third_code)

        assert stock is not None
        assert stock.symbol == "000001"
        assert stock.name == "平安银行"
