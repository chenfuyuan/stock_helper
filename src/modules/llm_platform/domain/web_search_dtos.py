from typing import List, Optional
from pydantic import BaseModel


class WebSearchRequest(BaseModel):
    """
    Web 搜索请求 DTO
    
    Attributes:
        query: 搜索查询词（必填）
        freshness: 时效过滤，可选值: oneDay / oneWeek / oneMonth / oneYear / noLimit
        summary: 是否生成 AI 摘要，默认 True
        count: 返回结果条数，默认 10
    """
    query: str
    freshness: Optional[str] = None
    summary: bool = True
    count: int = 10


class WebSearchResultItem(BaseModel):
    """
    单条搜索结果 DTO
    
    Attributes:
        title: 标题
        url: URL
        snippet: 摘要片段
        summary: AI 生成的摘要（当请求 summary=True 时有值）
        site_name: 网站名称
        published_date: 发布日期
    """
    title: str
    url: str
    snippet: str
    summary: Optional[str] = None
    site_name: Optional[str] = None
    published_date: Optional[str] = None


class WebSearchResponse(BaseModel):
    """
    Web 搜索响应 DTO
    
    Attributes:
        query: 原始查询词
        total_matches: 匹配总数（可选）
        results: 搜索结果列表
    """
    query: str
    total_matches: Optional[int] = None
    results: List[WebSearchResultItem]

    def to_prompt_context(self) -> str:
        """
        将搜索结果转换为 LLM 友好的上下文格式字符串
        
        Returns:
            Formatted search results string for LLM prompt context
        """
        context_parts = [f"Web Search Results for: '{self.query}'\n"]
        
        for i, item in enumerate(self.results, 1):
            # 优先使用 summary，如果没有则使用 snippet
            content = item.summary if item.summary else item.snippet
            date_info = f" ({item.published_date})" if item.published_date else ""
            source = item.site_name if item.site_name else "Unknown Source"
            
            context_parts.append(
                f"[{i}] Title: {item.title}\n"
                f"Source: {source}{date_info}\n"
                f"URL: {item.url}\n"
                f"Content: {content}\n"
            )
            
        return "\n".join(context_parts)
