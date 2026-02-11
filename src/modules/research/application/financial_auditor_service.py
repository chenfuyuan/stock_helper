"""
财务审计员 Application 接口。
对外暴露独立入口：入参 symbol，出参为包含解析结果与 input/output 的完整响应（由代码塞入，非大模型拼接）。
"""
from typing import Any

from src.shared.domain.exceptions import BadRequestException
from src.modules.research.domain.ports.financial_data import IFinancialDataPort
from src.modules.research.domain.ports.financial_snapshot_builder import (
    IFinancialSnapshotBuilder,
)
from src.modules.research.domain.ports.financial_auditor_agent import (
    IFinancialAuditorAgentPort,
)


class FinancialAuditorService:
    """
    财务审计员服务。Coordinator 仅调用本服务获取财务面评估，不共用其他专家入口。
    编排：校验 symbol → 获取财务数据 → 校验非空 → 构建快照 → 调用审计 Agent → 返回完整响应。
    """

    def __init__(
        self,
        financial_data_port: IFinancialDataPort,
        snapshot_builder: IFinancialSnapshotBuilder,
        auditor_agent_port: IFinancialAuditorAgentPort,
    ):
        self._financial_data = financial_data_port
        self._snapshot_builder = snapshot_builder
        self._auditor_agent = auditor_agent_port

    async def run(self, symbol: str, limit: int = 5) -> dict[str, Any]:
        """
        执行财务审计，返回包含解析结果与 input、financial_indicators、output 的字典（代码侧塞入）。
        解析失败由 Agent 实现层抛出 LLMOutputParseError。
        """
        if not symbol or not str(symbol).strip():
            raise BadRequestException(message="symbol 为必填")

        records = await self._financial_data.get_finance_records(
            ticker=symbol, limit=limit
        )
        if not records:
            raise BadRequestException(
                message=(
                    f"该标的 {symbol} 无财务数据。请先通过 data_engineering 同步该标的财务指标后再进行分析。"
                )
            )

        snapshot = self._snapshot_builder.build(records)
        agent_result = await self._auditor_agent.audit(symbol=symbol, snapshot=snapshot)

        result_dto = agent_result.result
        return {
            "financial_score": result_dto.financial_score,
            "signal": result_dto.signal,
            "confidence": result_dto.confidence,
            "summary_reasoning": result_dto.summary_reasoning,
            "dimension_analyses": [d.model_dump() for d in result_dto.dimension_analyses],
            "key_risks": result_dto.key_risks,
            "risk_warning": result_dto.risk_warning,
            "input": agent_result.user_prompt,
            "financial_indicators": snapshot.model_dump(),
            "output": agent_result.raw_llm_output,
        }
