"""
外部 API 调用日志 ORM 模型，映射表 external_api_call_logs。

模型定义在 shared 供多模块复用；写入由各模块的 Application 层（如 WebSearchService）负责。
"""
import uuid
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.shared.infrastructure.db.base import Base


class ExternalAPICallLogModel(Base):
    """外部 API 调用日志表。"""

    __tablename__ = "external_api_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="记录唯一标识")
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="关联 session")
    service_name = Column(String(50), nullable=False, comment="服务名（bochai / tushare / ...）")
    operation = Column(String(100), nullable=False, comment="操作（web-search / ...）")
    request_params = Column(JSONB, nullable=True, comment="请求参数")
    response_data = Column(Text, nullable=True, comment="完整响应")
    status_code = Column(Integer, nullable=True, comment="HTTP 状态码")
    latency_ms = Column(Integer, nullable=False, comment="调用耗时（毫秒）")
    status = Column(String(20), nullable=False, comment="success / failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, nullable=False, comment="记录时间")
