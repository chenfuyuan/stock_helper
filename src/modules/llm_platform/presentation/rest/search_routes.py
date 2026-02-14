import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.modules.llm_platform.application.services.web_search_service import (
    WebSearchService,
)
from src.modules.llm_platform.domain.exceptions import (
    WebSearchConfigError,
    WebSearchConnectionError,
    WebSearchError,
)
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
)
from src.modules.llm_platform.infrastructure.adapters.bocha_web_search import (
    BochaWebSearchAdapter,
)
from src.modules.llm_platform.infrastructure.config import llm_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-platform/web-search", tags=["LLM Platform - Web Search"])


# Presentation DTOs
class WebSearchApiRequest(BaseModel):
    """
    Web 搜索 API 请求 DTO
    """

    query: str = Field(..., description="搜索查询词（必填）")
    freshness: Optional[str] = Field(
        None,
        description="时效过滤: oneDay / oneWeek / oneMonth / oneYear / noLimit",
    )
    summary: bool = Field(True, description="是否生成 AI 摘要")
    count: int = Field(10, ge=1, le=50, description="返回结果条数")


class WebSearchApiResultItem(BaseModel):
    """
    单条搜索结果 DTO
    """

    title: str
    url: str
    snippet: str
    summary: Optional[str] = None
    site_name: Optional[str] = None
    published_date: Optional[str] = None


class WebSearchApiResponse(BaseModel):
    """
    Web 搜索 API 响应 DTO
    """

    query: str
    total_matches: Optional[int] = None
    results: List[WebSearchApiResultItem]


# Dependency
def get_web_search_service() -> WebSearchService:
    """
    装配 Web 搜索服务（通过依赖注入）

    Returns:
        WebSearchService: 装配好的搜索服务实例
    """
    # 从 settings 获取博查配置
    adapter = BochaWebSearchAdapter(
        api_key=llm_config.BOCHA_API_KEY, base_url=llm_config.BOCHA_BASE_URL
    )
    return WebSearchService(provider=adapter)


@router.post("/", response_model=WebSearchApiResponse)
async def search_web(
    request: WebSearchApiRequest,
    service: WebSearchService = Depends(get_web_search_service),
):
    """
    Web 搜索接口

    功能描述：
    接收搜索查询词和参数，调用博查 AI Web Search API 进行搜索。

    参数:
    - request: WebSearchApiRequest 请求体，包含 query（必填）、freshness、summary、count 等

    返回:
    - WebSearchApiResponse: 包含搜索结果列表

    异常:
    - 422: 请求参数校验失败（如 query 缺失）
    - 502: 上游搜索 API 错误
    - 503: 服务不可用（配置缺失或网络连接失败）
    - 500: 其他未预期错误
    """
    logger.info(
        f"API: search_web called. Query={request.query}, Freshness={request.freshness}, "  # noqa: E501
        f"Count={request.count}"
    )

    try:
        # 转换为 Domain DTO
        domain_request = WebSearchRequest(
            query=request.query,
            freshness=request.freshness,
            summary=request.summary,
            count=request.count,
        )

        # 调用服务执行搜索
        response = await service.search(domain_request)

        # 转换为 API 响应 DTO
        api_results = [
            WebSearchApiResultItem(
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                summary=item.summary,
                site_name=item.site_name,
                published_date=item.published_date,
            )
            for item in response.results
        ]

        logger.info(f"API: search_web completed successfully, returned {len(api_results)} results")

        return WebSearchApiResponse(
            query=response.query,
            total_matches=response.total_matches,
            results=api_results,
        )

    except WebSearchConfigError as e:
        # 配置错误 → 503
        logger.error(f"API: search_web - 配置错误: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

    except WebSearchConnectionError as e:
        # 网络连接错误 → 503
        logger.error(f"API: search_web - 连接错误: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

    except WebSearchError as e:
        # 搜索 API 错误 → 502
        logger.error(f"API: search_web - 搜索错误: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        # 其他未预期错误 → 500
        logger.error(f"API: search_web - 未知错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
