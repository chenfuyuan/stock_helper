from datetime import date

from src.modules.data_engineering.application.queries.get_broken_board_by_date import (
    GetBrokenBoardByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_limit_up_pool_by_date import (
    GetLimitUpPoolByDateUseCase,
)
from src.modules.data_engineering.application.queries.get_previous_limit_up_by_date import (
    GetPreviousLimitUpByDateUseCase,
)
from src.modules.market_insight.domain.dtos.sentiment_dtos import (
    BrokenBoardItemDTO,
    LimitUpPoolItemDTO,
    PreviousLimitUpItemDTO,
)
from src.modules.market_insight.domain.ports.sentiment_data_port import ISentimentDataPort


class DeSentimentDataAdapter(ISentimentDataPort):
    """
    DE 市场情绪数据适配器（MI 基础设施层）
    实现 ISentimentDataPort 接口，桥接 DataEngineering 模块
    将 DE 领域实体转换为 MI 领域层 DTO
    """

    def __init__(
        self,
        limit_up_pool_use_case: GetLimitUpPoolByDateUseCase,
        broken_board_use_case: GetBrokenBoardByDateUseCase,
        previous_limit_up_use_case: GetPreviousLimitUpByDateUseCase,
    ):
        self.limit_up_pool_use_case = limit_up_pool_use_case
        self.broken_board_use_case = broken_board_use_case
        self.previous_limit_up_use_case = previous_limit_up_use_case

    async def get_limit_up_pool(self, trade_date: date) -> list[LimitUpPoolItemDTO]:
        """
        获取指定日期的涨停池数据
        """
        entities = await self.limit_up_pool_use_case.execute(trade_date)

        return [
            LimitUpPoolItemDTO(
                third_code=entity.third_code,
                stock_name=entity.stock_name,
                pct_chg=entity.pct_chg,
                close=entity.close,
                amount=entity.amount,
                consecutive_boards=entity.consecutive_boards,
                industry=entity.industry,
            )
            for entity in entities
        ]

    async def get_broken_board_pool(self, trade_date: date) -> list[BrokenBoardItemDTO]:
        """
        获取指定日期的炸板池数据
        """
        entities = await self.broken_board_use_case.execute(trade_date)

        return [
            BrokenBoardItemDTO(
                third_code=entity.third_code,
                stock_name=entity.stock_name,
                pct_chg=entity.pct_chg,
                close=entity.close,
                amount=entity.amount,
                open_count=entity.open_count,
                industry=entity.industry,
            )
            for entity in entities
        ]

    async def get_previous_limit_up(self, trade_date: date) -> list[PreviousLimitUpItemDTO]:
        """
        获取昨日涨停今日表现数据
        """
        entities = await self.previous_limit_up_use_case.execute(trade_date)

        return [
            PreviousLimitUpItemDTO(
                third_code=entity.third_code,
                stock_name=entity.stock_name,
                pct_chg=entity.pct_chg,
                close=entity.close,
                amount=entity.amount,
                yesterday_consecutive_boards=entity.yesterday_consecutive_boards,
                industry=entity.industry,
            )
            for entity in entities
        ]
