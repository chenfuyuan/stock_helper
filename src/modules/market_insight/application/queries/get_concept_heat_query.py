"""
查询概念热度
"""

from datetime import date
from typing import List, Optional

from src.modules.market_insight.application.dtos.market_insight_dtos import (
    ConceptHeatDTO,
)
from src.modules.market_insight.domain.ports.repositories.concept_heat_repo import (
    IConceptHeatRepository,
)


class GetConceptHeatQuery:
    """查询概念热度"""

    def __init__(self, concept_heat_repo: IConceptHeatRepository):
        self._repo = concept_heat_repo

    async def execute(
        self, trade_date: date, top_n: Optional[int] = None
    ) -> List[ConceptHeatDTO]:
        """
        执行查询
        :param trade_date: 交易日期
        :param top_n: 仅返回前 N 条，None 表示返回全部
        :return: 概念热度 DTO 列表，按 avg_pct_chg 降序
        """
        heats = await self._repo.get_by_date(trade_date, top_n)

        return [
            ConceptHeatDTO(
                trade_date=h.trade_date,
                concept_code=h.concept_code,
                concept_name=h.concept_name,
                avg_pct_chg=h.avg_pct_chg,
                stock_count=h.stock_count,
                up_count=h.up_count,
                down_count=h.down_count,
                limit_up_count=h.limit_up_count,
                total_amount=h.total_amount,
            )
            for h in heats
        ]
