from datetime import date

from src.modules.data_engineering.application.dtos.market_data_query_dtos import (
    DragonTigerDTO,
)
from src.modules.data_engineering.domain.ports.repositories.dragon_tiger_repo import (
    IDragonTigerRepository,
)


class GetDragonTigerByDateUseCase:
    """
    按日期查询龙虎榜数据用例。

    返回 DTO 而非 Domain Entity，确保跨模块接口不暴露内部实体。
    """

    def __init__(self, dragon_tiger_repo: IDragonTigerRepository):
        self.dragon_tiger_repo = dragon_tiger_repo

    async def execute(self, trade_date: date) -> list[DragonTigerDTO]:
        """
        查询指定日期的龙虎榜记录。

        Args:
            trade_date: 交易日期

        Returns:
            龙虎榜 DTO 列表
        """
        entities = await self.dragon_tiger_repo.get_by_date(trade_date)
        return [
            DragonTigerDTO(
                trade_date=e.trade_date,
                third_code=e.third_code,
                stock_name=e.stock_name,
                pct_chg=e.pct_chg,
                close=e.close,
                reason=e.reason,
                net_amount=e.net_amount,
                buy_amount=e.buy_amount,
                sell_amount=e.sell_amount,
                buy_seats=e.buy_seats,
                sell_seats=e.sell_seats,
            )
            for e in entities
        ]
