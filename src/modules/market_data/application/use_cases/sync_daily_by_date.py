from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from src.modules.market_data.domain.repositories import StockDailyRepository
from src.modules.market_data.domain.services import StockDataProvider

class SyncDailyByDateUseCase:
    """
    用例：同步指定日期的所有股票日线数据
    """
    def __init__(
        self,
        daily_repo: StockDailyRepository,
        data_provider: StockDataProvider
    ):
        self.daily_repo = daily_repo
        self.data_provider = data_provider

    async def execute(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        执行同步
        :param trade_date: 交易日期，格式 YYYYMMDD。如果不传则默认为今天。
        """
        if not trade_date:
            trade_date = datetime.now().strftime("%Y%m%d")
            
        logger.info(f"Syncing daily data for date: {trade_date}...")
        
        try:
            # 1. 从数据源获取指定日期的全市场数据
            dailies = await self.data_provider.fetch_daily(trade_date=trade_date)
            
            if not dailies:
                logger.warning(f"No daily records found for {trade_date}")
                return {
                    "success": False,
                    "count": 0,
                    "message": f"No data found for {trade_date} (Market might be closed)"
                }
                
            logger.info(f"Fetched {len(dailies)} records for {trade_date}. Saving to DB...")
            
            # 2. 批量入库
            # 注意：这里是一次性事务，如果数据量特别大（A股目前约5000+），
            # 如果内存或数据库压力大，可能需要分批。
            # 但目前 5000 条对于批量插入来说通常是可接受的。
            saved_count = await self.daily_repo.save_all(dailies)
            
            logger.info(f"Successfully synced {saved_count} daily records for {trade_date}")
            
            return {
                "success": True,
                "count": saved_count,
                "message": f"Successfully synced {saved_count} records for {trade_date}"
            }
            
        except Exception as e:
            logger.error(f"Failed to sync daily data for {trade_date}: {str(e)}")
            raise e
