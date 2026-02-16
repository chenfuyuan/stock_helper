"""龙虎榜数据同步 Command。"""

from datetime import date

from loguru import logger

from src.modules.data_engineering.domain.model.dragon_tiger import DragonTigerDetail
from src.modules.data_engineering.domain.ports.providers.dragon_tiger_provider import (
    IDragonTigerProvider,
)
from src.modules.data_engineering.domain.ports.repositories.dragon_tiger_repo import (
    IDragonTigerRepository,
)


class SyncDragonTigerCmd:
    """
    同步龙虎榜数据命令。
    
    从 AkShare 获取龙虎榜数据并写入 PostgreSQL。
    """

    def __init__(
        self,
        dragon_tiger_provider: IDragonTigerProvider,
        dragon_tiger_repo: IDragonTigerRepository,
    ):
        self.dragon_tiger_provider = dragon_tiger_provider
        self.dragon_tiger_repo = dragon_tiger_repo

    async def execute(self, trade_date: date) -> int:
        """
        执行龙虎榜数据同步。
        
        Args:
            trade_date: 交易日期
            
        Returns:
            同步条数
            
        Raises:
            Exception: 同步失败时抛出
        """
        logger.info(f"开始同步龙虎榜数据：{trade_date}")
        
        dragon_tiger_dtos = await self.dragon_tiger_provider.fetch_dragon_tiger_detail(
            trade_date
        )
        
        if not dragon_tiger_dtos:
            logger.info(f"龙虎榜数据为空：{trade_date}")
            return 0
        
        dragon_tiger_entities = [
            DragonTigerDetail(
                trade_date=trade_date,
                third_code=dto.third_code,
                stock_name=dto.stock_name,
                pct_chg=dto.pct_chg,
                close=dto.close,
                reason=dto.reason,
                net_amount=dto.net_amount,
                buy_amount=dto.buy_amount,
                sell_amount=dto.sell_amount,
                buy_seats=dto.buy_seats,
                sell_seats=dto.sell_seats,
            )
            for dto in dragon_tiger_dtos
        ]
        
        count = await self.dragon_tiger_repo.save_all(dragon_tiger_entities)
        logger.info(f"龙虎榜数据同步成功：{count} 条")
        
        return count
