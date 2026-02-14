"""
估值建模师 Application 接口。
对外暴露独立入口：入参 symbol，出参为包含解析结果与 input/output 的完整响应（由代码塞入，非大模型拼接）。
"""

import logging
from datetime import date, timedelta
from typing import Any

from src.modules.research.domain.ports.valuation_data import IValuationDataPort
from src.modules.research.domain.ports.valuation_modeler_agent import (
    IValuationModelerAgentPort,
)
from src.modules.research.domain.ports.valuation_snapshot_builder import (
    IValuationSnapshotBuilder,
)
from src.shared.domain.exceptions import BadRequestException

DEFAULT_HISTORICAL_YEARS = 3  # 默认获取 3 年历史估值日线

logger = logging.getLogger(__name__)


class ValuationModelerService:
    """
    估值建模师服务。Coordinator 调用本服务获取估值建模结果，不共用其他专家入口。
    编排：校验 symbol → 获取股票概览（校验非空）→ 获取历史估值日线（默认 3 年）
    → 获取财务数据（校验非空）→ 构建估值快照 → 调用估值 Agent → 返回完整响应。
    """

    def __init__(
        self,
        valuation_data_port: IValuationDataPort,
        snapshot_builder: IValuationSnapshotBuilder,
        modeler_agent_port: IValuationModelerAgentPort,
    ):
        self._valuation_data = valuation_data_port
        self._snapshot_builder = snapshot_builder
        self._modeler_agent = modeler_agent_port

    async def run(self, symbol: str) -> dict[str, Any]:
        """
        执行估值建模，返回包含解析结果与 input、valuation_indicators、output 的字典（代码侧塞入）。
        解析失败由 Agent 实现层抛出 LLMOutputParseError。
        """
        # 校验 symbol 必填
        if not symbol or not str(symbol).strip():
            raise BadRequestException(message="symbol 为必填")

        # 获取股票概览（校验非空，表示标的存在）
        overview = await self._valuation_data.get_stock_overview(symbol=symbol)
        if overview is None:
            raise BadRequestException(
                message=f"该标的 {symbol} 不存在。请确认标的代码正确且已同步基础数据。"
            )

        # 获取历史估值日线（默认 3 年）
        end_date = date.today()
        start_date = end_date - timedelta(days=DEFAULT_HISTORICAL_YEARS * 365)
        historical_valuations = await self._valuation_data.get_valuation_dailies(
            ticker=symbol, start_date=start_date, end_date=end_date
        )
        if not historical_valuations:
            logger.warning(
                "估值建模师：历史估值日线为空，symbol=%s，时间范围=%s ~ %s，将继续使用财务数据构建快照。",
                symbol,
                start_date.isoformat(),
                end_date.isoformat(),
            )

        # 获取财务数据（校验非空）
        finance_records = await self._valuation_data.get_finance_for_valuation(
            ticker=symbol, limit=8
        )
        if not finance_records:
            raise BadRequestException(
                message=f"该标的 {symbol} 无财务数据，无法进行估值建模。请先通过 data_engineering 同步该标的财务指标后再进行分析。"
            )

        # 构建估值快照（预计算所有模型）
        snapshot = self._snapshot_builder.build(
            overview=overview,
            historical_valuations=historical_valuations,
            finance_records=finance_records,
        )

        # 调用估值 Agent
        agent_result = await self._modeler_agent.analyze(symbol=symbol, snapshot=snapshot)

        # 组装完整响应（含 narrative_report，供 coordinator 持久化 NodeExecution 与展示）
        result_dto = agent_result.result
        return {
            "valuation_verdict": result_dto.valuation_verdict,
            "confidence_score": result_dto.confidence_score,
            "estimated_intrinsic_value_range": result_dto.estimated_intrinsic_value_range.model_dump(),
            "key_evidence": result_dto.key_evidence,
            "risk_factors": result_dto.risk_factors,
            "reasoning_summary": result_dto.reasoning_summary,
            "narrative_report": result_dto.narrative_report,
            "input": agent_result.user_prompt,
            "valuation_indicators": snapshot.model_dump(),
            "output": agent_result.raw_llm_output,
        }
