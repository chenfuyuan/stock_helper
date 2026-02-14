"""
技术分析 Agent Port 的 Infrastructure 实现。
负责加载/填充 Prompt、调用 LLM、解析结果，并返回 DTO + 原始 input/output（由代码塞入，非大模型拼接）。
"""

from pathlib import Path
from typing import Optional

from src.modules.research.domain.dtos.indicators_snapshot import (
    TechnicalIndicatorsSnapshot,
)
from src.modules.research.domain.dtos.technical_analysis_dtos import (
    TechnicalAnalysisAgentResult,
)
from src.modules.research.domain.ports.llm import ILLMPort
from src.modules.research.domain.ports.technical_analyst_agent import (
    ITechnicalAnalystAgentPort,
)
from src.modules.research.infrastructure.agents.technical_analyst.output_parser import (
    parse_technical_analysis_result,
)
from src.modules.research.infrastructure.prompt_loader import (
    fill_user_prompt,
    load_system_prompt,
    load_user_prompt_template,
)


class TechnicalAnalystAgentAdapter(ITechnicalAnalystAgentPort):
    """加载 Prompt、填充占位符、调用 LLM、解析 JSON，返回结果与原始 input/output。"""

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None):
        self._llm = llm_port
        self._prompts_dir = prompts_dir

    async def analyze(
        self,
        ticker: str,
        analysis_date: str,
        snapshot: TechnicalIndicatorsSnapshot,
    ) -> TechnicalAnalysisAgentResult:
        system_prompt = load_system_prompt(self._prompts_dir)
        user_template = load_user_prompt_template(self._prompts_dir)
        user_prompt = fill_user_prompt(
            template=user_template,
            ticker=ticker,
            analysis_date=analysis_date,
            snapshot=snapshot,
        )
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.3,
        )
        result_dto = parse_technical_analysis_result(raw)
        return TechnicalAnalysisAgentResult(
            result=result_dto,
            raw_llm_output=raw,
            user_prompt=user_prompt,
        )
