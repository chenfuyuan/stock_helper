from datetime import date

from src.modules.data_engineering.application.dtos.market_data_query_dtos import (
    LimitUpPoolDTO,
)
from src.modules.data_engineering.domain.ports.repositories.limit_up_pool_repo import (
    ILimitUpPoolRepository,
)


class GetLimitUpPoolByDateUseCase:
    """
    按日期查询涨停池数据用例。

    返回 DTO 而非 Domain Entity，确保跨模块接口不暴露内部实体。
    """

    def __init__(self, limit_up_pool_repo: ILimitUpPoolRepository):
        self.limit_up_pool_repo = limit_up_pool_repo

    async def execute(self, trade_date: date) -> list[LimitUpPoolDTO]:
        """
        查询指定日期的涨停池记录。

        Args:
            trade_date: 交易日期

        Returns:
            涨停池 DTO 列表
        """
        entities = await self.limit_up_pool_repo.get_by_date(trade_date)
        return [
            LimitUpPoolDTO(
                trade_date=e.trade_date,
                third_code=e.third_code,
                stock_name=e.stock_name,
                pct_chg=e.pct_chg,
                close=e.close,
                amount=e.amount,
                turnover_rate=e.turnover_rate,
                consecutive_boards=e.consecutive_boards,
                first_limit_up_time=e.first_limit_up_time,
                last_limit_up_time=e.last_limit_up_time,
                industry=e.industry,
            )
            for e in entities
        ]
