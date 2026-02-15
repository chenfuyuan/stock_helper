"""
概念热度持久化接口
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.modules.market_insight.domain.model.concept_heat import ConceptHeat


class IConceptHeatRepository(ABC):
    """概念热度持久化接口"""
    
    @abstractmethod
    async def save_all(self, heats: List[ConceptHeat]) -> int:
        """
        批量 UPSERT 概念热度数据
        :param heats: 概念热度实体列表
        :return: 影响行数
        """
        pass
    
    @abstractmethod
    async def get_by_date(
        self, trade_date: date, top_n: Optional[int] = None
    ) -> List[ConceptHeat]:
        """
        查询指定日期的板块热度
        :param trade_date: 交易日期
        :param top_n: 仅返回前 N 条，None 表示返回全部
        :return: 概念热度列表，按 avg_pct_chg 降序
        """
        pass
    
    @abstractmethod
    async def get_by_concept_and_date_range(
        self, concept_code: str, start_date: date, end_date: date
    ) -> List[ConceptHeat]:
        """
        查询指定概念在日期范围内的热度历史
        :param concept_code: 概念代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 概念热度历史列表
        """
        pass
