"""
DebateGatewayAdapter：实现 IDebateGateway，将会话隔离、per-expert 字段映射、过滤调试字段，
调用 DebateContainer → DebateService，返回 dict。
"""
from typing import Any

from src.modules.debate.container import DebateContainer
from src.modules.debate.domain.dtos.debate_input import DebateInput, ExpertSummary
from src.modules.coordinator.domain.ports.debate_gateway import IDebateGateway


# 专家类型到 (signal_key, confidence_key, reasoning_key, risk_key) 的映射；
# risk 可能为 list，需 join 为字符串
_EXPERT_FIELD_MAP = {
    "technical_analyst": ("signal", "confidence", "summary_reasoning", "risk_warning"),
    "financial_auditor": ("signal", "confidence", "summary_reasoning", "risk_warning"),
    "valuation_modeler": (
        "valuation_verdict",
        "confidence_score",
        "reasoning_summary",
        "risk_factors",
    ),
    "macro_intelligence": (
        "macro_environment",
        "confidence_score",
        "macro_summary",
        "key_risks",
    ),
    "catalyst_detective": (
        ("result", "catalyst_assessment"),
        ("result", "confidence_score"),
        ("result", "catalyst_summary"),
        ("result", "negative_catalysts"),
    ),
}


def _get_nested(data: dict[str, Any], keys: str | tuple) -> Any:
    """若 keys 为 tuple (e.g. ('result','catalyst_assessment')) 则逐层取。"""
    if isinstance(keys, str):
        return data.get(keys)
    current = data
    for k in keys:
        current = (current or {}).get(k) if isinstance(current, dict) else None
    return current


def _to_str_list(val: Any) -> str:
    """将 risk 字段（可能为 list 或 str）转为字符串。"""
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(x) for x in val)
    return str(val)


def _to_float(val: Any) -> float:
    """安全转为 float。"""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _expert_result_to_summary(expert_key: str, data: Any) -> ExpertSummary | None:
    """
    将单专家结果 dict 转为 ExpertSummary。
    仅当 data 为 dict 且能提取出至少 signal 或 reasoning 时返回，否则返回 None。
    """
    if not isinstance(data, dict):
        return None
    mapping = _EXPERT_FIELD_MAP.get(expert_key)
    if not mapping:
        return None
    sig_key, conf_key, reason_key, risk_key = mapping
    signal_raw = _get_nested(data, sig_key)
    signal = str(signal_raw) if signal_raw is not None else ""
    confidence = _to_float(_get_nested(data, conf_key))
    reasoning = _get_nested(data, reason_key)
    reasoning = str(reasoning) if reasoning is not None else ""
    risk_raw = _get_nested(data, risk_key)
    risk_warning = _to_str_list(risk_raw)
    return ExpertSummary(
        signal=signal,
        confidence=confidence,
        reasoning=reasoning,
        risk_warning=risk_warning,
    )


class DebateGatewayAdapter(IDebateGateway):
    """
    通过 DebateContainer 获取 DebateService，将 expert_results 转为 DebateInput，
    调用 run() 后返回 DebateOutcomeDTO 的 dict 形式。
    """

    def __init__(self, session_factory: Any) -> None:
        """
        与 ResearchGatewayAdapter 一致，接受 session_factory 以保持接口统一。
        Debate 模块不依赖 DB，run_debate 内不创建 AsyncSession。
        """
        self._session_factory = session_factory

    async def run_debate(
        self, symbol: str, expert_results: dict[str, Any]
    ) -> dict[str, Any]:
        """
        仅包含成功的专家结果（由调用方保证）；过滤调试字段，按映射表归一化为 ExpertSummary，
        调用 DebateService.run 后返回 .model_dump()。
        """
        summaries: dict[str, ExpertSummary] = {}
        for expert_key, payload in expert_results.items():
            summary = _expert_result_to_summary(expert_key, payload)
            if summary is not None:
                summaries[expert_key] = summary
        debate_input = DebateInput(symbol=symbol, expert_summaries=summaries)
        container = DebateContainer()
        service = container.debate_service()
        outcome = await service.run(debate_input)
        return outcome.model_dump()
