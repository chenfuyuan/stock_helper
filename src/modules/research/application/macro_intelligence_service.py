"""
宏观情报员 Application 接口。

对外暴露独立入口：入参 symbol，出参为包含解析结果与 input/output/macro_indicators 的完整响应（由代码塞入，非大模型拼接）。
"""

from typing import Any

from src.modules.research.domain.ports.macro_context_builder import (
    IMacroContextBuilder,
)
from src.modules.research.domain.ports.macro_data import IMacroDataPort
from src.modules.research.domain.ports.macro_intelligence_agent import (
    IMacroIntelligenceAgentPort,
)
from src.shared.domain.exceptions import BadRequestException


class MacroIntelligenceService:
    """
    宏观情报员服务。Coordinator 仅调用本服务获取宏观面评估，不共用其他专家入口。

    编排流程：
    1. 校验 symbol
    2. 获取股票概览（名称、行业、代码）
    3. 执行四维度宏观搜索
    4. 校验搜索结果非全空
    5. 构建宏观上下文
    6. 调用宏观分析 Agent
    7. 返回完整响应（解析结果 + input + macro_indicators + output）
    """

    def __init__(
        self,
        macro_data_port: IMacroDataPort,
        context_builder: IMacroContextBuilder,
        agent_port: IMacroIntelligenceAgentPort,
    ):
        """
        初始化宏观情报员服务。

        Args:
            macro_data_port: 宏观数据 Port（获取股票信息 + 执行搜索）
            context_builder: 宏观上下文构建器（将搜索结果转为 Prompt 上下文）
            agent_port: 宏观情报员 Agent Port（调用 LLM 进行宏观分析）
        """
        self._macro_data = macro_data_port
        self._context_builder = context_builder
        self._agent = agent_port

    async def run(self, symbol: str) -> dict[str, Any]:
        """
        执行宏观情报分析，返回包含解析结果与 input、macro_indicators、output 的字典（代码侧塞入）。

        Args:
            symbol: 股票代码（如 '000001.SZ'）

        Returns:
            dict[str, Any]: 包含以下字段的完整响应：
                - macro_environment: 宏观环境判定（Favorable/Neutral/Unfavorable）
                - confidence_score: 置信度（0.0-1.0）
                - macro_summary: 宏观环境综合判断
                - dimension_analyses: 四维分析列表
                - key_opportunities: 宏观机会列表
                - key_risks: 宏观风险列表
                - information_sources: 信息来源 URL 列表
                - input: 发送给 LLM 的 user prompt
                - macro_indicators: 宏观上下文快照（MacroContextDTO 序列化）
                - output: LLM 原始返回字符串

        Raises:
            BadRequestException: symbol 缺失、标的不存在、或宏观搜索全部失败时
            LLMOutputParseError: LLM 返回内容无法解析时（由 Agent 层抛出）
            LLMError: LLM 调用失败时（由 Agent 层抛出）
        """
        # 1. 校验 symbol
        if not symbol or not str(symbol).strip():
            raise BadRequestException(message="symbol 为必填")

        # 2. 获取股票概览
        overview = await self._macro_data.get_stock_overview(symbol)
        if overview is None:
            raise BadRequestException(
                message=f"该标的 {symbol} 不存在。请确认股票代码是否正确。"
            )

        # 3. 执行四维度宏观搜索
        search_results = await self._macro_data.search_macro_context(
            industry=overview.industry,
            stock_name=overview.stock_name,
        )

        # 4. 校验搜索结果非全空（如果四个维度全部为空，则无法进行宏观分析）
        total_items = sum(len(r.items) for r in search_results)
        if total_items == 0:
            raise BadRequestException(
                message=(
                    f"宏观搜索全部失败（四个维度均无搜索结果），无法进行宏观分析。"
                    f"请检查 Web 搜索服务配置（BOCHA_API_KEY）或稍后重试。"
                )
            )

        # 5. 构建宏观上下文
        macro_context = self._context_builder.build(
            overview=overview,
            search_results=search_results,
        )

        # 6. 调用宏观分析 Agent
        agent_result = await self._agent.analyze(
            symbol=symbol,
            macro_context=macro_context,
        )

        # 7. 组装完整响应（解析结果 + input + macro_indicators + output）
        result_dto = agent_result.result
        return {
            "macro_environment": result_dto.macro_environment,
            "confidence_score": result_dto.confidence_score,
            "macro_summary": result_dto.macro_summary,
            "dimension_analyses": [
                d.model_dump() for d in result_dto.dimension_analyses
            ],
            "key_opportunities": result_dto.key_opportunities,
            "key_risks": result_dto.key_risks,
            "information_sources": result_dto.information_sources,
            "narrative_report": result_dto.narrative_report,
            "input": agent_result.user_prompt,
            "macro_indicators": macro_context.model_dump(),
            "output": agent_result.raw_llm_output,
        }
