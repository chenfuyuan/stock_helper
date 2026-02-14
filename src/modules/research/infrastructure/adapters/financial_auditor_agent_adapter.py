"""
财务审计 Agent Port 的 Infrastructure 实现。
负责加载/填充 Prompt、调用 LLM、解析结果，并返回 DTO + 原始 input/output（由代码塞入，非大模型拼接）。
"""

from pathlib import Path
from typing import Optional

from src.modules.research.domain.dtos.financial_dtos import (
    FinancialAuditAgentResult,
)
from src.modules.research.domain.dtos.financial_snapshot import (
    FinancialSnapshotDTO,
)
from src.modules.research.domain.ports.financial_auditor_agent import (
    IFinancialAuditorAgentPort,
)
from src.modules.research.domain.ports.llm import ILLMPort
from src.modules.research.infrastructure.agents.financial_auditor.output_parser import (
    parse_financial_audit_result,
)
from src.modules.research.infrastructure.prompt_loader import (
    fill_financial_auditor_user_prompt,
    load_financial_auditor_system_prompt,
    load_financial_auditor_user_template,
)

_FINANCIAL_AUDITOR_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent / "agents" / "financial_auditor" / "prompts"
)


class FinancialAuditorAgentAdapter(IFinancialAuditorAgentPort):
    """加载 Prompt、填充占位符、调用 LLM、解析 JSON，返回结果与原始 input/output。"""

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None):
        self._llm = llm_port
        self._prompts_dir = prompts_dir or _FINANCIAL_AUDITOR_PROMPTS_DIR

    async def audit(
        self,
        symbol: str,
        snapshot: FinancialSnapshotDTO,
    ) -> FinancialAuditAgentResult:
        system_prompt = load_financial_auditor_system_prompt(self._prompts_dir)
        user_template = load_financial_auditor_user_template(self._prompts_dir)
        user_prompt = fill_financial_auditor_user_prompt(
            template=user_template,
            snapshot=snapshot,
        )
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.3,
        )
        result_dto = parse_financial_audit_result(raw)
        return FinancialAuditAgentResult(
            result=result_dto,
            raw_llm_output=raw,
            user_prompt=user_prompt,
        )
