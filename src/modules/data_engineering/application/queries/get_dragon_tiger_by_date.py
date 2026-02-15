from datetime import date

from src.modules.data_engineering.domain.model.dragon_tiger import DragonTigerDetail
from src.modules.data_engineering.domain.ports.repositories.dragon_tiger_repo import (
    IDragonTigerRepository,
)
from src.shared.application.use_cases import BaseUseCase


class GetDragonTigerByDateUseCase(BaseUseCase):
    """
    按日期查询龙虎榜数据用例
    """

    def __init__(self, dragon_tiger_repo: IDragonTigerRepository):
        self.dragon_tiger_repo = dragon_tiger_repo

    async def execute(self, trade_date: date) -> list[DragonTigerDetail]:
        """
        查询指定日期的龙虎榜记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[DragonTigerDetail]: 龙虎榜记录列表
        """
        return await self.dragon_tiger_repo.get_by_date(trade_date)
