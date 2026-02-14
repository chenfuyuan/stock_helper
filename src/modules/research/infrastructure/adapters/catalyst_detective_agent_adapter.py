import logging
from pathlib import Path
from typing import Optional

from src.modules.research.domain.dtos.catalyst_context import (
    CatalystContextDTO,
)
from src.modules.research.domain.dtos.catalyst_dtos import (
    CatalystDetectiveAgentResult,
)
from src.modules.research.domain.ports.catalyst_detective_agent import (
    ICatalystDetectiveAgentPort,
)
from src.modules.research.domain.ports.llm import ILLMPort
from src.modules.research.infrastructure import prompt_loader
from src.modules.research.infrastructure.agents.catalyst_detective.output_parser import (
    parse_catalyst_detective_result,
)

logger = logging.getLogger(__name__)


class CatalystDetectiveAgentAdapter(ICatalystDetectiveAgentPort):
    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None):
        """
        初始化催化剂侦探 Agent 适配器

        :param llm_port: LLM Port 实现
        :param prompts_dir: Prompt 文件夹路径，默认相对于 prompt_loader
        """
        self.llm_port = llm_port

        # Resolve default prompts directory relative to prompt_loader path structure
        # Expected: src/modules/research/infrastructure/agents/catalyst_detective/prompts
        if prompts_dir:
            self.prompts_dir = prompts_dir
        else:
            base_dir = Path(prompt_loader.__file__).resolve().parent
            self.prompts_dir = (
                base_dir / "agents" / "catalyst_detective" / "prompts"
            )

    async def analyze(
        self, symbol: str, catalyst_context: CatalystContextDTO
    ) -> CatalystDetectiveAgentResult:
        """
        调用 LLM 对催化剂上下文进行分析，返回结构化结果
        """
        # Load prompts
        system_prompt = prompt_loader.load_catalyst_detective_system_prompt(
            self.prompts_dir
        )
        user_template = prompt_loader.load_catalyst_detective_user_template(
            self.prompts_dir
        )

        if not system_prompt or not user_template:
            logger.error(
                f"Failed to load prompts from {self.prompts_dir}. "
                f"System: {bool(system_prompt)}, User: {bool(user_template)}"
            )
            # Maybe raise exception here? But let's let LLM call handle empty prompt or just proceed (likely error later)
            # ILLMPort might handle empty prompt but let's be safe.

        # Fill prompts
        user_prompt = prompt_loader.fill_catalyst_detective_user_prompt(
            user_template, catalyst_context
        )

        # Call LLM
        # Using a slightly lower temperature (0.3) for more analytical stability
        raw_output = await self.llm_port.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.3,
        )

        # Parse output
        result_dto = parse_catalyst_detective_result(raw_output)

        return CatalystDetectiveAgentResult(
            result=result_dto,
            raw_llm_output=raw_output,
            user_prompt=user_prompt,
            catalyst_context=catalyst_context,
        )
