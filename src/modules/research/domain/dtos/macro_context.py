"""
宏观上下文 DTO。

定义填充 User Prompt 模板所需的宏观上下文数据结构。
该 DTO 的字段与 user.md 模板中的占位符一一对应。
"""

from pydantic import BaseModel, Field


class MacroContextDTO(BaseModel):
    """
    宏观分析上下文，包含股票基础信息与四个维度的宏观情报上下文。

    该 DTO 的 9 个字段与 user.md Prompt 模板中的占位符一一对应：
    - stock_name：股票名称
    - third_code：第三方代码（如 000001.SZ）
    - industry：所属行业
    - current_date：当前日期（格式如"2026-02-13"）
    - monetary_context：货币与流动性维度的搜索情报文本
    - policy_context：产业政策与监管维度的搜索情报文本
    - economic_context：宏观经济周期维度的搜索情报文本
    - industry_context：行业景气与资金流向维度的搜索情报文本
    - all_source_urls：所有搜索结果的来源 URL 列表（格式化为字符串）

    Context Builder 负责将搜索结果按维度归类并格式化为这些文本字段。
    """

    stock_name: str = Field(..., description="股票名称")
    third_code: str = Field(..., description="第三方代码（如 000001.SZ）")
    industry: str = Field(..., description="所属行业")
    current_date: str = Field(..., description="当前日期（格式如'2026-02-13'）")
    monetary_context: str = Field(..., description="货币与流动性维度的搜索情报文本")
    policy_context: str = Field(..., description="产业政策与监管维度的搜索情报文本")
    economic_context: str = Field(..., description="宏观经济周期维度的搜索情报文本")
    industry_context: str = Field(..., description="行业景气与资金流向维度的搜索情报文本")
    all_source_urls: str = Field(..., description="所有搜索结果的来源 URL 列表（格式化为字符串）")
