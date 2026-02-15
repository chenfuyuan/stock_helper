"""
查询涨停股
"""

from datetime import date
from typing import List, Optional

from src.modules.market_insight.application.dtos.market_insight_dtos import (
    LimitUpStockDTO,
)
from src.modules.market_insight.domain.ports.repositories.limit_up_repo import (
    ILimitUpRepository,
)


class GetLimitUpQuery:
    """查询涨停股"""

    def __init__(self, limit_up_repo: ILimitUpRepository):
        self._repo = limit_up_repo

    async def execute(
        self, trade_date: date, concept_code: Optional[str] = None
    ) -> List[LimitUpStockDTO]:
        """
        执行查询
        :param trade_date: 交易日期
        :param concept_code: 概念代码（可选，用于过滤）
        :return: 涨停股 DTO 列表
        """
        if concept_code:
            stocks = await self._repo.get_by_date_and_concept(trade_date, concept_code)
        else:
            stocks = await self._repo.get_by_date(trade_date)

        return [
            LimitUpStockDTO(
                trade_date=s.trade_date,
                third_code=s.third_code,
                stock_name=s.stock_name,
                pct_chg=s.pct_chg,
                close=s.close,
                amount=s.amount,
                concept_codes=s.concept_codes,
                concept_names=s.concept_names,
                limit_type=s.limit_type.value,
            )
            for s in stocks
        ]
