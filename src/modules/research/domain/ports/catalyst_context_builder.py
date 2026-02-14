from abc import ABC, abstractmethod
from typing import List

from src.modules.research.domain.dtos.catalyst_context import (
    CatalystContextDTO,
)
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
    CatalystStockOverview,
)


class ICatalystContextBuilder(ABC):
    @abstractmethod
    def build(
        self,
        overview: CatalystStockOverview,
        search_results: List[CatalystSearchResult],
    ) -> CatalystContextDTO:
        """
        根据股票概览和多维度搜索结果，构建填充 Prompt 所需的上下文 DTO
        """
