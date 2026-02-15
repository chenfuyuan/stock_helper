from datetime import date

from src.modules.data_engineering.domain.model.broken_board import BrokenBoardStock
from src.modules.data_engineering.domain.ports.repositories.broken_board_repo import (
    IBrokenBoardRepository,
)
from src.shared.application.use_cases import BaseUseCase


class GetBrokenBoardByDateUseCase(BaseUseCase):
    """
    按日期查询炸板池数据用例
    """

    def __init__(self, broken_board_repo: IBrokenBoardRepository):
        self.broken_board_repo = broken_board_repo

    async def execute(self, trade_date: date) -> list[BrokenBoardStock]:
        """
        查询指定日期的炸板池记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[BrokenBoardStock]: 炸板池记录列表
        """
        return await self.broken_board_repo.get_by_date(trade_date)
