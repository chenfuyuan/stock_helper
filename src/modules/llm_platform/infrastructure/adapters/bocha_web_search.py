import logging
from typing import Any, Dict

import httpx

from src.modules.llm_platform.domain.exceptions import (
    WebSearchConfigError,
    WebSearchConnectionError,
    WebSearchError,
)
from src.modules.llm_platform.domain.ports.web_search import IWebSearchProvider
from src.modules.llm_platform.domain.web_search_dtos import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResultItem,
)

logger = logging.getLogger(__name__)


class BochaWebSearchAdapter(IWebSearchProvider):
    """
    博查 AI Web Search API 适配器

    实现 IWebSearchProvider 接口，调用博查 AI Web Search API (POST /v1/web-search)
    将博查 API 的响应映射为标准的 WebSearchResponse DTO

    Attributes:
        api_key: 博查 API Key
        base_url: 博查 API 基础 URL（默认 https://api.bochaai.com）
        timeout: HTTP 请求超时时间（秒，默认 30）
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bochaai.com",
        timeout: int = 30,
    ):
        """
        初始化博查搜索适配器

        Args:
            api_key: 博查 API Key
            base_url: 博查 API 基础 URL
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """
        执行 Web 搜索

        Args:
            request: 搜索请求

        Returns:
            WebSearchResponse: 搜索结果

        Raises:
            WebSearchConfigError: API Key 未配置
            WebSearchConnectionError: 网络连接/超时错误
            WebSearchError: API 错误或响应格式异常
        """
        # 检查 API Key 是否配置
        if not self.api_key or self.api_key.strip() == "":
            logger.error("博查 API Key 未配置")
            raise WebSearchConfigError("博查 API Key 未配置，请设置 BOCHA_API_KEY 环境变量")

        # 构建请求体
        request_body = self._build_request_body(request)
        logger.info(f"执行博查搜索，查询词: {request.query}, 请求体: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/web-search",
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                # 处理 HTTP 错误
                if response.status_code >= 400:
                    error_msg = f"博查 API 返回错误，状态码: {response.status_code}"
                    logger.error(error_msg)
                    try:
                        error_detail = response.json()
                        error_msg += f", 详情: {error_detail}"
                    except Exception:
                        error_msg += f", 响应: {response.text[:200]}"
                    raise WebSearchError(error_msg)

                # 解析响应
                response_data = response.json()
                logger.info(f"博查 API 原始响应: {response_data}")
                return self._map_response(request.query, response_data)

        except httpx.TimeoutException as e:
            logger.error(f"博查 API 请求超时: {e}")
            raise WebSearchConnectionError(f"博查 API 请求超时: {e}")
        except httpx.ConnectError as e:
            logger.error(f"博查 API 连接失败: {e}")
            raise WebSearchConnectionError(f"博查 API 连接失败: {e}")
        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.error(f"博查 API 网络错误: {e}")
            raise WebSearchConnectionError(f"博查 API 网络错误: {e}")
        except WebSearchError:
            # 重新抛出已处理的业务错误
            raise
        except WebSearchConnectionError:
            # 重新抛出已处理的连接错误
            raise
        except Exception as e:
            logger.error(f"博查搜索发生未知错误: {e}")
            raise WebSearchError(f"博查搜索发生未知错误: {e}")

    def _build_request_body(self, request: WebSearchRequest) -> Dict[str, Any]:
        """
        构建博查 API 请求体

        Args:
            request: 搜索请求 DTO

        Returns:
            博查 API 请求体字典
        """
        body: Dict[str, Any] = {
            "query": request.query,
            "summary": request.summary,
            "count": request.count,
        }

        # 可选参数：时效过滤
        if request.freshness:
            body["freshness"] = request.freshness

        return body

    def _map_response(self, query: str, response_data: Dict[str, Any]) -> WebSearchResponse:
        """
        将博查 API 响应映射为标准 WebSearchResponse DTO

        Args:
            query: 原始查询词
            response_data: 博查 API 响应数据

        Returns:
            WebSearchResponse: 标准搜索响应
        """
        # 防御性解析：博查 API 响应结构为 {code, data: {webPages: {...}}}
        logger.debug(f"响应数据结构: keys={list(response_data.keys())}")

        # 提取 data 字段（博查 API 的实际响应结构）
        data = response_data.get("data", {})
        web_pages = data.get("webPages", {})

        logger.debug(f"webPages 结构: {web_pages}")
        value_list = web_pages.get("value", [])
        logger.info(f"value_list 长度: {len(value_list)}")

        # 映射结果列表
        results = []
        for item in value_list:
            result_item = WebSearchResultItem(
                title=item.get("name", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                summary=item.get("summary"),
                site_name=item.get("siteName"),
                published_date=item.get("datePublished"),
            )
            results.append(result_item)

        # 获取匹配总数（可选字段）
        total_matches = web_pages.get("totalEstimatedMatches")

        logger.info(f"博查搜索完成，返回 {len(results)} 条结果")

        return WebSearchResponse(
            query=query,
            total_matches=total_matches,
            results=results,
        )
