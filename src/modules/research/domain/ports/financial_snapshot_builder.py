"""
构建财务快照的 Port。
Domain 层仅定义契约；具体实现在 Infrastructure 层。
Application 通过此 Port 获取快照，不直接依赖实现。
"""

from abc import ABC, abstractmethod
from typing import List

from src.modules.research.domain.dtos.financial_record_input import (
    FinanceRecordInput,
)
from src.modules.research.domain.dtos.financial_snapshot import (
    FinancialSnapshotDTO,
)


class IFinancialSnapshotBuilder(ABC):
    """入参多期财务数据 DTO 列表，出参与 User Prompt 模板一致的 FinancialSnapshotDTO。"""

    @abstractmethod
    def build(self, records: List[FinanceRecordInput]) -> FinancialSnapshotDTO:
        raise NotImplementedError
