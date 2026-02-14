from typing import Any, Dict

from loguru import logger

from src.modules.data_engineering.domain.ports.providers.market_quote_provider import (
    IMarketQuoteProvider,
)
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)


class SyncDailyHistoryUseCase:
    """
    同步股票日线历史数据用例
    """

    def __init__(
        self,
        stock_repo: IStockBasicRepository,
        daily_repo: IMarketQuoteRepository,
        data_provider: IMarketQuoteProvider,
    ):
        self.stock_repo = stock_repo
        self.daily_repo = daily_repo
        self.data_provider = data_provider

    async def execute(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        执行同步逻辑（支持分页）

        改为纯串行调用，限速完全由 TushareClient 的 _rate_limited_call 统一处理。
        移除了 Semaphore 和 sleep 等 Application 层的限速代码。
        """
        target_stocks = await self.stock_repo.get_all(skip=offset, limit=limit)

        if not target_stocks:
            logger.warning(f"未找到需要同步的股票 (offset={offset}, limit={limit})")
            return {
                "synced_stocks": 0,
                "total_rows": 0,
                "message": f"未找到需要同步的股票 (offset={offset}, limit={limit})",
            }

        logger.info(f"开始同步 {len(target_stocks)} 只股票的历史日线数据 (offset={offset})...")

        synced_stocks_count = 0
        total_rows_saved = 0

        # 串行处理每只股票：拉取 -> 保存
        for stock in target_stocks:
            try:
                if not stock.third_code:
                    logger.warning(f"股票 {stock.name} 缺少 third_code，跳过")
                    continue

                logger.info(f"正在拉取 {stock.third_code} ({stock.name}) 的历史日线数据...")
                dailies = await self.data_provider.fetch_daily(third_code=stock.third_code)

                if dailies:
                    logger.info(f"成功拉取 {len(dailies)} 条记录，准备写入数据库...")
                    saved_count = await self.daily_repo.save_all(dailies)
                    total_rows_saved += saved_count
                    synced_stocks_count += 1
                    logger.info(f"成功保存 {stock.third_code} 的 {saved_count} 条日线记录")
                else:
                    logger.warning(f"{stock.third_code} 没有返回日线数据")

            except Exception as e:
                logger.error(f"同步 {stock.third_code} 失败: {str(e)}")
                # 单只股票失败不中断整批，继续处理下一只
                continue

        return {
            "synced_stocks": synced_stocks_count,
            "total_rows": total_rows_saved,
            "message": f"成功同步 {synced_stocks_count} 只股票，共 {total_rows_saved} 条日线记录",
        }
