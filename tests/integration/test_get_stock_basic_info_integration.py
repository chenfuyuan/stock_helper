import pytest
from datetime import date
from app.infrastructure.repositories.stock_repository import StockRepositoryImpl
from app.infrastructure.repositories.stock_daily_repository import StockDailyRepositoryImpl
from app.application.stock.use_cases.get_stock_basic_info import GetStockBasicInfoUseCase
from app.domain.stock.entities import StockInfo, StockDaily
from app.domain.stock.enums import MarketType, ListStatus

@pytest.mark.asyncio
async def test_get_stock_basic_info_integration(db_session):
    """
    集成测试：GetStockBasicInfoUseCase
    使用真实的数据库会话 (db_session fixture 提供了事务回滚，保证测试数据不污染)
    """
    
    # 1. 准备测试数据
    symbol = "TEST001"
    third_code = "TEST001.SZ"
    
    # 创建并保存 StockInfo
    stock_info = StockInfo(
        symbol=symbol,
        third_code=third_code,
        name="集成测试股票",
        market=MarketType.MAIN,
        list_status=ListStatus.LISTED,
        list_date=date(2023, 1, 1)
    )
    
    # 创建并保存 StockDaily (保存两天数据以验证获取最新的一条)
    daily_old = StockDaily(
        third_code=third_code,
        trade_date=date(2023, 1, 1),
        open=10.0, high=11.0, low=9.0, close=10.5,
        pre_close=10.0, change=0.5, pct_chg=5.0,
        vol=1000, amount=10000
    )
    
    daily_new = StockDaily(
        third_code=third_code,
        trade_date=date(2023, 1, 2), # 更新的日期
        open=10.5, high=12.0, low=10.0, close=11.5,
        pre_close=10.5, change=1.0, pct_chg=9.5,
        vol=2000, amount=23000
    )
    
    # 2. 初始化真实的 Repository 实现
    stock_repo = StockRepositoryImpl(db_session)
    daily_repo = StockDailyRepositoryImpl(db_session)
    
    # 3. 将测试数据写入数据库
    await stock_repo.save(stock_info)
    await daily_repo.save_all([daily_old, daily_new])
    
    # 确保数据已 flush 到数据库 (但在事务内)
    await db_session.flush()
    
    # 4. 初始化 Use Case
    use_case = GetStockBasicInfoUseCase(stock_repo, daily_repo)
    
    # 5. 执行 Use Case
    result = await use_case.execute(symbol)
    
    # 6. 验证结果
    assert result is not None
    assert result.info.symbol == symbol
    assert result.info.name == "集成测试股票"
    
    assert result.daily is not None
    # 验证获取的是最新日期的数据 (2023-01-02)
    assert result.daily.trade_date == date(2023, 1, 2)
    assert result.daily.close == 11.5
    
    # 7. 验证不存在的情况
    result_none = await use_case.execute("NON_EXISTENT")
    assert result_none is None
