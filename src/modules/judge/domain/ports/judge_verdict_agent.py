"""
裁决 Agent Port。

定义单次综合裁决的抽象接口，由 Infrastructure Adapter 实现。
"""

from abc import ABC, abstractmethod

from src.modules.judge.domain.dtos.judge_input import JudgeInput
from src.modules.judge.domain.dtos.verdict_result import VerdictResult


class IJudgeVerdictAgentPort(ABC):
    """裁决 Agent 抽象接口：根据 JudgeInput 执行单次 LLM 裁决，返回 VerdictResult。"""

    @abstractmethod
    async def judge(self, input: JudgeInput) -> VerdictResult:
        """执行裁决，返回领域 DTO。"""
        raise NotImplementedError
