"""
Bull Advocate Agent Port 的 Infrastructure 实现。

加载 Prompt → 填充 DebateInput 占位符 → 调用 ILLMPort → 解析 → 返回 BullArgument。
"""

from pathlib import Path
from typing import Optional

from src.modules.debate.domain.dtos.debate_input import DebateInput
from src.modules.debate.domain.ports.bull_advocate_agent import (
    IBullAdvocateAgentPort,
)
from src.modules.debate.domain.ports.llm import ILLMPort
from src.modules.debate.infrastructure.agents.bull_advocate.output_parser import (
    parse_bull_argument,
)
from src.modules.debate.infrastructure.prompt_loader import (
    fill_bull_user_prompt,
    get_prompts_dir,
    load_system_prompt,
    load_user_prompt_template,
)


def _format_expert_summary(d: DebateInput, key: str) -> str:
    """将某专家的 ExpertSummary 格式化为一段摘要文本，缺失时返回 '(无)'。"""
    summary = d.expert_summaries.get(key)
    if not summary:
        return "(无)"
    return (
        f"信号: {summary.signal} | 置信度: {summary.confidence}\n"
        f"推理: {summary.reasoning}\n"
        f"风险提示: {summary.risk_warning}"
    )


class BullAdvocateAgentAdapter(IBullAdvocateAgentPort):
    """加载 Prompt、填充占位符、调用 LLM、解析 JSON，返回 BullArgument。"""

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None) -> None:
        self._llm = llm_port
        self._prompts_dir = prompts_dir or get_prompts_dir("bull_advocate")

    async def advocate(self, input_data: DebateInput) -> "BullArgument":
        pass

        system_prompt = load_system_prompt(self._prompts_dir)
        user_template = load_user_prompt_template(self._prompts_dir)
        user_prompt = fill_bull_user_prompt(
            template=user_template,
            symbol=input_data.symbol,
            technical_analyst_summary=_format_expert_summary(input_data, "technical_analyst"),
            financial_auditor_summary=_format_expert_summary(input_data, "financial_auditor"),
            valuation_modeler_summary=_format_expert_summary(input_data, "valuation_modeler"),
            macro_intelligence_summary=_format_expert_summary(input_data, "macro_intelligence"),
            catalyst_detective_summary=_format_expert_summary(input_data, "catalyst_detective"),
        )
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.3,
        )
        return parse_bull_argument(raw)
