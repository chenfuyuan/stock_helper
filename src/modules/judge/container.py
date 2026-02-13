"""
Judge 模块 Composition Root。

装配 LLMAdapter → JudgeVerdictAgentAdapter → JudgeService。
"""
from src.modules.judge.application.services.judge_service import JudgeService
from src.modules.judge.infrastructure.adapters.judge_verdict_agent_adapter import (
    JudgeVerdictAgentAdapter,
)
from src.modules.judge.infrastructure.adapters.llm_adapter import LLMAdapter


def _get_llm_service():
    """延迟导入避免循环依赖。"""
    from src.modules.llm_platform.container import LLMPlatformContainer
    return LLMPlatformContainer().llm_service()


class JudgeContainer:
    """Judge 模块的依赖组装容器。"""

    def __init__(self) -> None:
        self._llm_service = _get_llm_service()
        self._llm_adapter = LLMAdapter(llm_service=self._llm_service)
        self._verdict_agent = JudgeVerdictAgentAdapter(llm_port=self._llm_adapter)
        self._judge_service = JudgeService(verdict_agent=self._verdict_agent)

    def judge_service(self) -> JudgeService:
        """返回装配好的 JudgeService。"""
        return self._judge_service
