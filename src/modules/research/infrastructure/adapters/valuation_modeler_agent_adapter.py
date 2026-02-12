"""
估值建模 Agent Port 的 Infrastructure 实现。
负责加载/填充 Prompt、调用 LLM、解析结果，并返回 DTO + 原始 input/output（由代码塞入，非大模型拼接）。
"""
from pathlib import Path
from typing import Optional

from src.modules.research.domain.valuation_dtos import ValuationModelAgentResult
from src.modules.research.agents.valuation_modeler.output_parser import (
    parse_valuation_result,
)
from src.modules.research.domain.ports.dto_valuation_inputs import ValuationSnapshotDTO
from src.modules.research.domain.ports.valuation_modeler_agent import (
    IValuationModelerAgentPort,
)
from src.modules.research.domain.ports.llm import ILLMPort
from src.modules.research.infrastructure.prompt_loader import (
    fill_valuation_modeler_user_prompt,
    load_valuation_modeler_system_prompt,
    load_valuation_modeler_user_template,
)

_VALUATION_MODELER_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "agents" / "valuation_modeler" / "prompts"
)


class ValuationModelerAgentAdapter(IValuationModelerAgentPort):
    """加载 Prompt、填充占位符、调用 LLM、解析 JSON，返回结果与原始 input/output。"""

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None):
        self._llm = llm_port
        self._prompts_dir = prompts_dir or _VALUATION_MODELER_PROMPTS_DIR

    async def analyze(
        self,
        symbol: str,
        snapshot: ValuationSnapshotDTO,
    ) -> ValuationModelAgentResult:
        """
        基于估值快照进行估值分析。
        加载 System Prompt 与 User Prompt 模板，填充占位符，调用 LLM，解析结果。
        解析失败时抛出 LLMOutputParseError。
        """
        system_prompt = load_valuation_modeler_system_prompt(self._prompts_dir)
        user_template = load_valuation_modeler_user_template(self._prompts_dir)
        user_prompt = fill_valuation_modeler_user_prompt(
            template=user_template,
            snapshot=snapshot,
        )
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.3,
        )
        result_dto = parse_valuation_result(raw)
        return ValuationModelAgentResult(
            result=result_dto,
            raw_llm_output=raw,
            user_prompt=user_prompt,
        )
