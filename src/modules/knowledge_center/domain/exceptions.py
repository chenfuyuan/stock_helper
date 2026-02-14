"""
Knowledge Center 领域异常。

所有异常继承 shared 的 AppException，便于 Presentation 层统一映射 HTTP 状态码。
"""

from typing import Any

from src.shared.domain.exceptions import AppException


class GraphSyncError(AppException):
    """图谱同步失败异常。"""

    def __init__(
        self,
        message: str = "图谱同步失败",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="GRAPH_SYNC_ERROR",
            status_code=500,
            details=details or {},
        )


class GraphQueryError(AppException):
    """图谱查询失败异常。"""

    def __init__(
        self,
        message: str = "图谱查询失败",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="GRAPH_QUERY_ERROR",
            status_code=500,
            details=details or {},
        )


class Neo4jConnectionError(AppException):
    """Neo4j 连接失败异常。"""

    def __init__(
        self,
        message: str = "Neo4j 连接失败",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code="NEO4J_CONNECTION_ERROR",
            status_code=503,
            details=details or {},
        )
