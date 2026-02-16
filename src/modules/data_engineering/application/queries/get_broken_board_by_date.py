from datetime import date

from src.modules.data_engineering.application.dtos.market_data_query_dtos import (
    BrokenBoardDTO,
)
from src.modules.data_engineering.domain.ports.repositories.broken_board_repo import (
    IBrokenBoardRepository,
)

class GetBrokenBoardByDateUseCase:
    """
    按日期查询炒板池数据用例。

    返回 DTO 而非 Domain Entity，确保跨模块接口不暴露内部实体。
    """

    def __init__(self, broken_board_repo: IBrokenBoardRepository):
        self.broken_board_repo = broken_board_repo

    async def execute(self, trade_date: date) -> list[BrokenBoardDTO]:
        """
        查询指定日期的炒板池记录。

        Args:
            trade_date: 交易日期

        Returns:
            炒板池 DTO 列表
        """
        entities = await self.broken_board_repo.get_by_date(trade_date)
        return [
            BrokenBoardDTO(
                trade_date=e.trade_date,
                third_code=e.third_code,
                stock_name=e.stock_name,
                pct_chg=e.pct_chg,
                close=e.close,
                amount=e.amount,
                turnover_rate=e.turnover_rate,
                open_count=e.open_count,
                first_limit_up_time=e.first_limit_up_time,
                last_open_time=e.last_open_time,
                industry=e.industry,
            )
            for e in entities
        ]
