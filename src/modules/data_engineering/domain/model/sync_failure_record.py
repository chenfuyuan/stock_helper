from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from src.modules.data_engineering.domain.model.enums import SyncJobType


@dataclass
class SyncFailureRecord:
    """
    同步失败记录实体
    
    用于记录单只股票在同步过程中的失败信息，支持自动重试机制。
    超过最大重试次数后需人工介入处理。
    """
    id: UUID = field(default_factory=uuid4)
    job_type: SyncJobType = SyncJobType.DAILY_HISTORY
    third_code: str = ""  # 失败的股票代码（Tushare ts_code 格式）
    error_message: str = ""  # 错误信息
    retry_count: int = 0  # 当前重试次数
    max_retries: int = 3  # 最大重试次数
    last_attempt_at: Optional[datetime] = None  # 最后一次尝试时间
    resolved_at: Optional[datetime] = None  # 解决时间（重试成功或人工标记）

    def can_retry(self) -> bool:
        """判断是否可以重试（未超过最大重试次数且未解决）"""
        return self.retry_count < self.max_retries and self.resolved_at is None

    def increment_retry(self) -> None:
        """递增重试次数并更新最后尝试时间"""
        self.retry_count += 1
        self.last_attempt_at = datetime.now()

    def resolve(self) -> None:
        """标记为已解决（重试成功或人工修复）"""
        self.resolved_at = datetime.now()

    def is_resolved(self) -> bool:
        """判断是否已解决"""
        return self.resolved_at is not None
