"""
技术分析师 Application 接口。
对外暴露独立入口：入参 ticker、analysis_date，出参为包含解析结果与 input/technical_indicators/output 的完整响应（由代码塞入，非大模型拼接）。
"""
from datetime import date, timedelta
from typing import Any, Optional

from src.shared.domain.exceptions import BadRequestException
from src.modules.research.domain.ports.indicator_calculator import IIndicatorCalculator
from src.modules.research.domain.ports.market_quote import IMarketQuotePort
from src.modules.research.domain.ports.technical_analyst_agent import ITechnicalAnalystAgentPort


class TechnicalAnalystService:
    """
    技术分析师服务。Coordinator 仅调用本服务获取技术面观点，不共用其他专家入口。
    编排：获取日线 → 通过 Port 计算技术指标 → 通过 Agent Port 分析 → 返回带 input/output 的完整响应。
    """

    def __init__(
        self,
        market_quote_port: IMarketQuotePort,
        indicator_calculator: IIndicatorCalculator,
        analyst_agent_port: ITechnicalAnalystAgentPort,
    ):
        self._market_quote = market_quote_port
        self._indicator_calculator = indicator_calculator
        self._analyst_agent = analyst_agent_port

    async def run(
        self,
        ticker: str,
        analysis_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        执行技术分析，返回包含解析结果与 input、technical_indicators、output 的字典（代码侧塞入）。
        解析失败由 Agent 实现层抛出 LLMOutputParseError。
        """
        if not ticker or not str(ticker).strip():
            raise BadRequestException(message="ticker 为必填")
        if analysis_date is None:
            raise BadRequestException(message="analysis_date 为必填")

        start_date = analysis_date - timedelta(days=365)
        bars = await self._market_quote.get_daily_bars(
            ticker=ticker, start_date=start_date, end_date=analysis_date
        )
        if not bars:
            raise BadRequestException(
                message=(
                    f"该标的 {ticker} 在区间 {start_date.isoformat()} ~ {analysis_date.isoformat()} 内无日线数据，"
                    "技术指标无法计算。请先通过 POST /api/v1/stocks/sync/daily 同步该标的日线后再进行分析。"
                )
            )
        snapshot = self._indicator_calculator.compute(bars)
        agent_result = await self._analyst_agent.analyze(
            ticker=ticker,
            analysis_date=analysis_date.isoformat(),
            snapshot=snapshot,
        )
        # 由代码组装响应体：解析结果 + 大模型 input、technical_indicators、output
        result_dto = agent_result.result
        return {
            "signal": result_dto.signal,
            "confidence": result_dto.confidence,
            "summary_reasoning": result_dto.summary_reasoning,
            "key_technical_levels": result_dto.key_technical_levels.model_dump(),
            "risk_warning": result_dto.risk_warning,
            "input": agent_result.user_prompt,
            "technical_indicators": snapshot.model_dump(),
            "output": agent_result.raw_llm_output,
        }
