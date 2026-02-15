"""
Market Insight 模块的领域异常定义
"""

from src.shared.domain.exceptions import AppException


class MarketInsightDomainException(AppException):
    """Market Insight 模块领域层异常基类"""
    pass


class InvalidConceptDataException(MarketInsightDomainException):
    """无效的概念数据异常"""
    pass


class InvalidMarketDataException(MarketInsightDomainException):
    """无效的市场数据异常"""
    pass
