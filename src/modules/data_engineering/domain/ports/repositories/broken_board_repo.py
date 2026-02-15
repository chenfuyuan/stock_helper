from abc import ABC, abstractmethod
from datetime import date

from src.modules.data_engineering.domain.model.broken_board import BrokenBoardStock


class IBrokenBoardRepository(ABC):
    """
    炸板池数据仓储 Port
    定义炸板池数据的持久化能力
    """

    @abstractmethod
    async def save_all(self, stocks: list[BrokenBoardStock]) -> int:
        """
        批量 UPSERT 炸板池记录（以 trade_date + third_code 为唯一键）
        
        Args:
            stocks: 炸板池股票列表
            
        Returns:
            int: 影响的行数
        """

    @abstractmethod
    async def get_by_date(self, trade_date: date) -> list[BrokenBoardStock]:
        """
        查询指定日期的炸板池记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[BrokenBoardStock]: 炸板池记录列表
        """
