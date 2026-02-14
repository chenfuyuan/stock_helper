"""
Debate 模块 Composition Root。

装配 LLMAdapter → BullAdvocateAgentAdapter / BearAdvocateAgentAdapter / ResolutionAgentAdapter → DebateService。
"""

from src.modules.debate.application.services.debate_service import (
    DebateService,
)
from src.modules.debate.infrastructure.adapters.bear_advocate_agent_adapter import (
    BearAdvocateAgentAdapter,
)
from src.modules.debate.infrastructure.adapters.bull_advocate_agent_adapter import (
    BullAdvocateAgentAdapter,
)
from src.modules.debate.infrastructure.adapters.llm_adapter import LLMAdapter
from src.modules.debate.infrastructure.adapters.resolution_agent_adapter import (
    ResolutionAgentAdapter,
)


def _get_llm_service():
    """延迟导入避免循环依赖。"""
    from src.modules.llm_platform.container import LLMPlatformContainer

    return LLMPlatformContainer().llm_service()


class DebateContainer:
    """Debate 模块的依赖组装容器。"""

    def __init__(self) -> None:
        self._llm_service = _get_llm_service()
        self._llm_adapter = LLMAdapter(llm_service=self._llm_service)
        self._bull_agent = BullAdvocateAgentAdapter(llm_port=self._llm_adapter)
        self._bear_agent = BearAdvocateAgentAdapter(llm_port=self._llm_adapter)
        self._resolution_agent = ResolutionAgentAdapter(llm_port=self._llm_adapter)
        self._debate_service = DebateService(
            bull_agent=self._bull_agent,
            bear_agent=self._bear_agent,
            resolution_agent=self._resolution_agent,
        )

    def debate_service(self) -> DebateService:
        """返回装配好的 DebateService。"""
        return self._debate_service
