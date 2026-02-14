"""
多头/空头论证 DTO。

由 Bull Advocate / Bear Advocate Agent 产出，供 Resolution Agent 消费。
"""

from pydantic import BaseModel


class BullArgument(BaseModel):
    """多头论证。"""

    direction: str  # 如 "BULLISH"
    confidence: float  # 0.0 - 1.0
    core_thesis: str  # 核心论点
    supporting_arguments: list[str]  # 各维度支持论点
    acknowledged_risks: list[str]  # 承认的风险
    price_catalysts: list[str]  # 识别的价格催化剂
    narrative_report: str = ""  # 面向人类的中文叙述性报告：核心结论、论据、风险、置信度


class BearArgument(BaseModel):
    """空头论证。"""

    direction: str  # 如 "BEARISH"
    confidence: float  # 0.0 - 1.0
    core_thesis: str  # 核心论点
    supporting_arguments: list[str]  # 各维度支持论点
    acknowledged_strengths: list[str]  # 承认的多头优势
    risk_triggers: list[str]  # 风险触发条件
    narrative_report: str = ""  # 面向人类的中文叙述性报告：核心结论、论据、风险、置信度
