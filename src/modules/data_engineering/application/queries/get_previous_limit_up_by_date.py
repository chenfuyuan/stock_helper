from datetime import date

from src.modules.data_engineering.application.dtos.market_data_query_dtos import (
    PreviousLimitUpDTO,
)
from src.modules.data_engineering.domain.ports.repositories.previous_limit_up_repo import (
    IPreviousLimitUpRepository,
)


class GetPreviousLimitUpByDateUseCase:
    """
    按日期查询昨日涨停表现数据用例。

    返回 DTO 而非 Domain Entity，确保跨模块接口不暴露内部实体。
    """

    def __init__(self, previous_limit_up_repo: IPreviousLimitUpRepository):
        self.previous_limit_up_repo = previous_limit_up_repo

    async def execute(self, trade_date: date) -> list[PreviousLimitUpDTO]:
        """
        查询指定日期的昨日涨停表现记录。

        Args:
            trade_date: 交易日期

        Returns:
            昨日涨停 DTO 列表
        """
        entities = await self.previous_limit_up_repo.get_by_date(trade_date)
        return [
            PreviousLimitUpDTO(
                trade_date=e.trade_date,
                third_code=e.third_code,
                stock_name=e.stock_name,
                pct_chg=e.pct_chg,
                close=e.close,
                amount=e.amount,
                turnover_rate=e.turnover_rate,
                yesterday_consecutive_boards=e.yesterday_consecutive_boards,
                industry=e.industry,
            )
            for e in entities
        ]
