import logging

from src.modules.llm_platform.domain.ports.web_search import IWebSearchProvider
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
)

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Web 搜索应用服务
    
    作为跨模块调用的 Application 入口，对外暴露搜索能力。
    通过依赖注入接收 IWebSearchProvider 实现，隐藏 Infrastructure 实现细节。
    
    Attributes:
        provider: Web 搜索提供商实现（通过 Port 抽象注入）
    """

    def __init__(self, provider: IWebSearchProvider):
        """
        初始化搜索服务
        
        Args:
            provider: Web 搜索提供商实现（实现 IWebSearchProvider 接口）
        """
        self.provider = provider

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """
        执行 Web 搜索
        
        Args:
            request: 搜索请求
            
        Returns:
            WebSearchResponse: 搜索结果
            
        Raises:
            WebSearchConfigError: 配置错误
            WebSearchConnectionError: 网络连接错误
            WebSearchError: 搜索错误
        """
        # 搜索前记录日志
        logger.info(f"开始搜索，查询词: {request.query}, 时效: {request.freshness}, 条数: {request.count}")

        # 委托 Provider 执行搜索
        response = await self.provider.search(request)

        # 搜索后记录结果日志
        logger.info(f"搜索完成，查询词: {request.query}, 返回结果数: {len(response.results)}")

        return response
