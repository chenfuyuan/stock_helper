"""
获取宏观分析所需数据的 Port。

Research 仅依赖此抽象，由 Infrastructure 的 Adapter 调用：
- data_engineering 的 Application 接口（获取股票基础信息）
- llm_platform 的 Application 接口（执行 Web 搜索）
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.research.domain.dtos.macro_inputs import (
    MacroSearchResult,
    MacroStockOverview,
)


class IMacroDataPort(ABC):
    """
    获取宏观情报员所需的两类数据：股票概览与宏观搜索结果。

    该 Port 聚合了两个不同上游模块的数据获取，但对 Application 层而言
    只是一个「获取宏观数据」的关注点，保持注入依赖数量一致。
    """

    @abstractmethod
    async def get_stock_overview(self, symbol: str) -> Optional[MacroStockOverview]:
        """
        获取股票基础信息（名称、行业、代码），用于宏观分析的上下文构建。

        该方法由 Adapter 内部调用 data_engineering 的 GetStockBasicInfoUseCase，
        提取所需字段转为 MacroStockOverview。

        Args:
            symbol: 股票代码（如 '000001.SZ'）

        Returns:
            MacroStockOverview: 股票概览信息
            None: 标的不存在时返回 None
        """
        raise NotImplementedError

    @abstractmethod
    async def search_macro_context(self, industry: str, stock_name: str) -> List[MacroSearchResult]:
        """
        基于行业与公司上下文，执行四个维度的宏观搜索。

        该方法由 Adapter 内部调用 llm_platform 的 WebSearchService，
        按四个维度分别构建搜索查询并执行：
        1. 货币与流动性环境
        2. 产业政策与监管动态
        3. 宏观经济周期定位
        4. 行业景气与资金流向

        每个维度的搜索独立 try/except，失败时返回空结果（不中断其他维度）。

        Args:
            industry: 所属行业（用于构建行业相关搜索查询）
            stock_name: 股票名称（可选择性用于增加搜索精确度）

        Returns:
            List[MacroSearchResult]: 四个维度的搜索结果列表（每个 MacroSearchResult
                包含 dimension_topic 和该维度下的搜索条目 items）
        """
        raise NotImplementedError
