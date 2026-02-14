"""
Resolution Agent Port 的 Infrastructure 实现。

加载 Prompt → 填充 Bull/Bear 论证占位符 → 调用 ILLMPort → 解析 → 返回 ResolutionResult。
"""

from pathlib import Path
from typing import Optional

from src.modules.debate.domain.dtos.bull_bear_argument import (
    BearArgument,
    BullArgument,
)
from src.modules.debate.domain.dtos.resolution_result import ResolutionResult
from src.modules.debate.domain.ports.llm import ILLMPort
from src.modules.debate.domain.ports.resolution_agent import (
    IResolutionAgentPort,
)
from src.modules.debate.infrastructure.agents.resolution.output_parser import (
    parse_resolution_result,
)
from src.modules.debate.infrastructure.prompt_loader import (
    fill_resolution_user_prompt,
    get_prompts_dir,
    load_system_prompt,
    load_user_prompt_template,
)


def _list_to_detail(items: list[str]) -> str:
    """将列表格式化为多行文本。"""
    if not items:
        return "(无)"
    return "\n".join(f"- {x}" for x in items)


class ResolutionAgentAdapter(IResolutionAgentPort):
    """加载 Prompt、填充 Bull/Bear 论证、调用 LLM、解析 JSON，返回 ResolutionResult。"""

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None) -> None:
        self._llm = llm_port
        self._prompts_dir = prompts_dir or get_prompts_dir("resolution")

    async def resolve(self, bull_arg: BullArgument, bear_arg: BearArgument) -> ResolutionResult:
        pass

        system_prompt = load_system_prompt(self._prompts_dir)
        user_template = load_user_prompt_template(self._prompts_dir)
        user_prompt = fill_resolution_user_prompt(
            template=user_template,
            symbol="",
            bull_core_thesis=bull_arg.core_thesis,
            bull_confidence=bull_arg.confidence,
            bull_arguments_detail=_list_to_detail(bull_arg.supporting_arguments),
            bull_acknowledged_risks=_list_to_detail(bull_arg.acknowledged_risks),
            bull_price_catalysts=_list_to_detail(bull_arg.price_catalysts),
            bear_core_thesis=bear_arg.core_thesis,
            bear_confidence=bear_arg.confidence,
            bear_arguments_detail=_list_to_detail(bear_arg.supporting_arguments),
            bear_acknowledged_strengths=_list_to_detail(bear_arg.acknowledged_strengths),
            bear_risk_triggers=_list_to_detail(bear_arg.risk_triggers),
        )
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.2,
        )
        return parse_resolution_result(raw)
