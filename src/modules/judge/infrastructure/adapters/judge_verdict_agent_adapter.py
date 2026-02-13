"""
JudgeVerdictAgent Port 的 Infrastructure 实现。

加载 Prompt → 填充 JudgeInput 占位符 → 调用 ILLMPort → 解析 → 返回 VerdictResult。
"""
from pathlib import Path
from typing import Optional

from src.modules.judge.domain.dtos.judge_input import JudgeInput
from src.modules.judge.domain.dtos.verdict_result import VerdictResult
from src.modules.judge.domain.ports.judge_verdict_agent import IJudgeVerdictAgentPort
from src.modules.judge.domain.ports.llm_port import ILLMPort
from src.modules.judge.infrastructure.agents.verdict.output_parser import parse_verdict_result
from src.modules.judge.infrastructure.prompt_loader import (
    fill_user_prompt,
    get_prompts_dir,
    load_system_prompt,
    load_user_prompt_template,
)


def _list_to_bullets(items: list[str]) -> str:
    """将列表格式化为多行 bullet 文本。"""
    if not items:
        return "(无)"
    return "\n".join(f"- {x}" for x in items)


class JudgeVerdictAgentAdapter(IJudgeVerdictAgentPort):
    """加载 Prompt、填充 JudgeInput、调用 LLM、解析 JSON，返回 VerdictResult。"""

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None) -> None:
        self._llm = llm_port
        self._prompts_dir = prompts_dir or get_prompts_dir("verdict")

    async def judge(self, input: JudgeInput) -> VerdictResult:
        system_prompt = load_system_prompt(self._prompts_dir)
        user_template = load_user_prompt_template(self._prompts_dir)
        user_prompt = fill_user_prompt(
            template=user_template,
            symbol=input.symbol,
            direction=input.direction,
            confidence=input.confidence,
            bull_thesis=input.bull_thesis,
            bear_thesis=input.bear_thesis,
            risk_factors=_list_to_bullets(input.risk_factors),
            key_disagreements=_list_to_bullets(input.key_disagreements),
            conflict_resolution=input.conflict_resolution,
        )
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.2,
        )
        return parse_verdict_result(raw)
