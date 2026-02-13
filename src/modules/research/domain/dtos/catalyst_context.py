from pydantic import BaseModel


class CatalystContextDTO(BaseModel):
    """
    构建完成的催化剂上下文 DTO，用于填充 LLM Prompt
    字段与 user.md 中的 9 个占位符一一对应
    """

    stock_name: str
    third_code: str
    industry: str
    current_date: str
    company_events_context: str
    industry_catalyst_context: str
    market_sentiment_context: str
    earnings_context: str
    all_source_urls: str
