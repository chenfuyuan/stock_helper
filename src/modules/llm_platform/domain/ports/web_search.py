from abc import ABC, abstractmethod
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
)


class IWebSearchProvider(ABC):
    """
    Web 搜索提供商抽象接口
    
    该 Port 定义了搜索能力的标准契约，与 ILLMProvider 完全独立。
    Infrastructure 层的具体实现（如 BochaWebSearchAdapter）实现此接口。
    """

    @abstractmethod
    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """
        执行 Web 搜索
        
        Args:
            request: 搜索请求（包含 query、freshness、summary、count 等参数）
            
        Returns:
            WebSearchResponse: 搜索响应（包含结果列表）
            
        Raises:
            WebSearchConfigError: 配置错误（如 API Key 未设置）
            WebSearchConnectionError: 网络连接/超时错误
            WebSearchError: 通用搜索错误
        """
        pass
