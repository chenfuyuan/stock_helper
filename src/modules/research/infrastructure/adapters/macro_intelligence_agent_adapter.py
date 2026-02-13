"""
宏观情报员 Agent Port 的 Infrastructure 实现。

负责加载/填充 Prompt、调用 LLM、解析结果，并返回 DTO + 原始 input/output（由代码塞入，非大模型拼接）。
"""
from pathlib import Path
from typing import Optional

from src.modules.research.domain.dtos.macro_context import MacroContextDTO
from src.modules.research.domain.dtos.macro_dtos import MacroIntelligenceAgentResult
from src.modules.research.domain.ports.macro_intelligence_agent import (
    IMacroIntelligenceAgentPort,
)
from src.modules.research.domain.ports.llm import ILLMPort
from src.modules.research.infrastructure.agents.macro_intelligence.output_parser import (
    parse_macro_intelligence_result,
)
from src.modules.research.infrastructure.prompt_loader import (
    fill_macro_intelligence_user_prompt,
    load_macro_intelligence_system_prompt,
    load_macro_intelligence_user_template,
)

_MACRO_INTELLIGENCE_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent / "agents" / "macro_intelligence" / "prompts"
)


class MacroIntelligenceAgentAdapter(IMacroIntelligenceAgentPort):
    """
    宏观情报员 Agent Adapter 实现。
    
    加载 Prompt、填充占位符、调用 LLM、解析 JSON，返回结果与原始 input/output。
    """

    def __init__(self, llm_port: ILLMPort, prompts_dir: Optional[Path] = None):
        """
        初始化宏观情报员 Agent Adapter。
        
        Args:
            llm_port: LLM Port 实现（通过依赖注入）
            prompts_dir: Prompt 资源目录（默认为 agents/macro_intelligence/prompts）
        """
        self._llm = llm_port
        self._prompts_dir = prompts_dir or _MACRO_INTELLIGENCE_PROMPTS_DIR

    async def analyze(
        self, symbol: str, macro_context: MacroContextDTO
    ) -> MacroIntelligenceAgentResult:
        """
        执行宏观分析。
        
        基于宏观上下文调用 LLM 进行四维宏观扫描分析，
        返回宏观环境评估结果。
        
        Args:
            symbol: 股票代码（如 '000001.SZ'，用于日志记录）
            macro_context: 宏观上下文（包含股票信息与四维度搜索情报）
            
        Returns:
            MacroIntelligenceAgentResult: 包含解析后的宏观分析结果、
                原始 LLM 输出和 user prompt
                
        Raises:
            LLMOutputParseError: LLM 返回内容无法解析为 MacroIntelligenceResultDTO 时
            LLMError: LLM 调用失败时
        """
        # 1. 加载 Prompt 模板
        system_prompt = load_macro_intelligence_system_prompt(self._prompts_dir)
        user_template = load_macro_intelligence_user_template(self._prompts_dir)
        
        # 2. 填充占位符
        user_prompt = fill_macro_intelligence_user_prompt(
            template=user_template,
            macro_context=macro_context,
        )
        
        # 3. 调用 LLM
        raw = await self._llm.generate(
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.3,  # 使用较低的 temperature 以获得更稳定的输出
        )
        
        # 4. 解析结果
        result_dto = parse_macro_intelligence_result(raw)
        
        # 5. 返回完整结果（解析后的 DTO + 原始 output + user prompt）
        return MacroIntelligenceAgentResult(
            result=result_dto,
            raw_llm_output=raw,
            user_prompt=user_prompt,
        )
