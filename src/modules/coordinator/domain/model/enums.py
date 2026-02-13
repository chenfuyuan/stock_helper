"""
Coordinator Domain 枚举定义。

ExpertType 与 REST 请求体中的 experts 列表值一一对应，值为 snake_case 字符串。
"""
from enum import Enum


class ExpertType(str, Enum):
    """研究专家类型枚举。"""

    TECHNICAL_ANALYST = "technical_analyst"
    FINANCIAL_AUDITOR = "financial_auditor"
    VALUATION_MODELER = "valuation_modeler"
    MACRO_INTELLIGENCE = "macro_intelligence"
    CATALYST_DETECTIVE = "catalyst_detective"
