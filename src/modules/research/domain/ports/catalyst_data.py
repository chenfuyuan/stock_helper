from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
    CatalystStockOverview,
)


class ICatalystDataPort(ABC):
    @abstractmethod
    async def get_stock_overview(
        self, symbol: str
    ) -> Optional[CatalystStockOverview]:
        """
        获取股票基础概览信息 (名称/行业/代码)
        """

    @abstractmethod
    async def search_catalyst_context(
        self, stock_name: str, industry: str
    ) -> List[CatalystSearchResult]:
        """
        执行多维度的催化剂搜索，获取搜索结果列表
        """
