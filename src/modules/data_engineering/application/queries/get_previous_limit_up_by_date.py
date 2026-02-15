from datetime import date

from src.modules.data_engineering.domain.model.previous_limit_up import PreviousLimitUpStock
from src.modules.data_engineering.domain.ports.repositories.previous_limit_up_repo import (
    IPreviousLimitUpRepository,
)
from src.shared.application.use_cases import BaseUseCase


class GetPreviousLimitUpByDateUseCase(BaseUseCase):
    """
    按日期查询昨日涨停表现数据用例
    """

    def __init__(self, previous_limit_up_repo: IPreviousLimitUpRepository):
        self.previous_limit_up_repo = previous_limit_up_repo

    async def execute(self, trade_date: date) -> list[PreviousLimitUpStock]:
        """
        查询指定日期的昨日涨停表现记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[PreviousLimitUpStock]: 昨日涨停表现记录列表
        """
        return await self.previous_limit_up_repo.get_by_date(trade_date)
