"""
宏观情报员 Agent Port。

定义宏观分析的抽象接口，由 Infrastructure 层实现
（加载 Prompt、调用 LLM、解析输出）。
"""
from abc import ABC, abstractmethod

from src.modules.research.domain.dtos.macro_context import MacroContextDTO
from src.modules.research.domain.dtos.macro_dtos import MacroIntelligenceAgentResult


class IMacroIntelligenceAgentPort(ABC):
    """
    宏观情报员 Agent 接口。
    
    负责基于宏观上下文调用 LLM 进行宏观环境分析，
    返回解析后的宏观分析结果以及原始 LLM 输出和 user prompt。
    
    实现层负责：
    1. 加载 System Prompt 和 User Prompt 模板
    2. 用 MacroContextDTO 填充 User Prompt 占位符
    3. 调用 LLM（通过 ILLMPort）
    4. 解析 LLM 输出为 MacroIntelligenceResultDTO
    5. 返回完整的 MacroIntelligenceAgentResult
    """

    @abstractmethod
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
        raise NotImplementedError
