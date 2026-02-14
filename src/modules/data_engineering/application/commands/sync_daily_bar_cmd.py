from typing import Any, Dict

from loguru import logger

from src.modules.data_engineering.domain.ports.providers.market_quote_provider import (
    IMarketQuoteProvider,
)
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)


class SyncDailyByDateUseCase:
    """
    用例：同步指定日期的所有股票日线数据
    """

    def __init__(
        self,
        daily_repo: IMarketQuoteRepository,
        data_provider: IMarketQuoteProvider,
    ):
        self.daily_repo = daily_repo
        self.data_provider = data_provider

    async def execute(self, trade_date: str) -> Dict[str, Any]:
        logger.info(f"Syncing daily bars for {trade_date}")

        dailies = await self.data_provider.fetch_daily(trade_date=trade_date)
        if not dailies:
            return {"status": "success", "count": 0, "message": "No data"}

        saved_count = await self.daily_repo.save_all(dailies)

        return {
            "status": "success",
            "count": saved_count,
            "message": f"Synced {saved_count} daily bars",
        }
