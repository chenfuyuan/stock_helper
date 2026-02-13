"""
宏观上下文构建器 Port。

定义将股票概览与搜索结果转为 Prompt 上下文的抽象。
"""
from abc import ABC, abstractmethod
from typing import List

from src.modules.research.domain.dtos.macro_inputs import (
    MacroStockOverview,
    MacroSearchResult,
)
from src.modules.research.domain.dtos.macro_context import MacroContextDTO


class IMacroContextBuilder(ABC):
    """
    宏观上下文构建器接口。
    
    负责将股票基础信息和多维度搜索结果结构化为 MacroContextDTO，
    该 DTO 的字段与 User Prompt 模板的占位符一一对应。
    
    处理逻辑包括：
    1. 按四个维度归类搜索结果，格式化为文本段落
    2. 提取去重的来源 URL 列表
    3. 处理空结果（标记为"信息有限"）
    4. 填充日期、股票信息等基础字段
    """

    @abstractmethod
    def build(
        self, overview: MacroStockOverview, search_results: List[MacroSearchResult]
    ) -> MacroContextDTO:
        """
        构建宏观上下文。
        
        将股票概览和搜索结果转为 MacroContextDTO，用于填充 User Prompt 模板。
        
        Args:
            overview: 股票概览信息（名称、行业、代码）
            search_results: 四个维度的搜索结果列表
            
        Returns:
            MacroContextDTO: 包含 9 个字段的宏观上下文（与 user.md 占位符一一对应）
        """
        raise NotImplementedError
