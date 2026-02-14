"""
Debate Prompt 运行时加载。

从 agents/<agent_name>/prompts 读取 system.md、user.md，提供 load_system_prompt、
load_user_prompt_template、fill_user_prompt 等工具函数（复用 Research 模式）。
"""

from pathlib import Path

# 默认以 infrastructure 为基准，agents 在其下
_BASE_AGENTS = Path(__file__).resolve().parent / "agents"


def load_system_prompt(prompts_dir: Path | None = None) -> str:
    """加载指定目录下的 system.md。"""
    if prompts_dir is None:
        return ""
    path = prompts_dir / "system.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_user_prompt_template(prompts_dir: Path | None = None) -> str:
    """加载指定目录下的 user.md 模板（含占位符）。"""
    if prompts_dir is None:
        return ""
    path = prompts_dir / "user.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def fill_bull_user_prompt(
    template: str,
    symbol: str,
    technical_analyst_summary: str,
    financial_auditor_summary: str,
    valuation_modeler_summary: str,
    macro_intelligence_summary: str,
    catalyst_detective_summary: str,
) -> str:
    """填充 Bull Advocate user prompt 占位符。专家摘要缺失时用占位文案。"""
    return template.format(
        symbol=symbol,
        technical_analyst_summary=technical_analyst_summary or "(无)",
        financial_auditor_summary=financial_auditor_summary or "(无)",
        valuation_modeler_summary=valuation_modeler_summary or "(无)",
        macro_intelligence_summary=macro_intelligence_summary or "(无)",
        catalyst_detective_summary=catalyst_detective_summary or "(无)",
    )


def fill_bear_user_prompt(
    template: str,
    symbol: str,
    technical_analyst_summary: str,
    financial_auditor_summary: str,
    valuation_modeler_summary: str,
    macro_intelligence_summary: str,
    catalyst_detective_summary: str,
) -> str:
    """填充 Bear Advocate user prompt 占位符。"""
    return template.format(
        symbol=symbol,
        technical_analyst_summary=technical_analyst_summary or "(无)",
        financial_auditor_summary=financial_auditor_summary or "(无)",
        valuation_modeler_summary=valuation_modeler_summary or "(无)",
        macro_intelligence_summary=macro_intelligence_summary or "(无)",
        catalyst_detective_summary=catalyst_detective_summary or "(无)",
    )


def fill_resolution_user_prompt(
    template: str,
    symbol: str,
    bull_core_thesis: str,
    bull_confidence: float,
    bull_arguments_detail: str,
    bull_acknowledged_risks: str,
    bull_price_catalysts: str,
    bear_core_thesis: str,
    bear_confidence: float,
    bear_arguments_detail: str,
    bear_acknowledged_strengths: str,
    bear_risk_triggers: str,
) -> str:
    """填充 Resolution user prompt 占位符。"""
    return template.format(
        symbol=symbol,
        bull_core_thesis=bull_core_thesis,
        bull_confidence=bull_confidence,
        bull_arguments_detail=bull_arguments_detail,
        bull_acknowledged_risks=bull_acknowledged_risks,
        bull_price_catalysts=bull_price_catalysts,
        bear_core_thesis=bear_core_thesis,
        bear_confidence=bear_confidence,
        bear_arguments_detail=bear_arguments_detail,
        bear_acknowledged_strengths=bear_acknowledged_strengths,
        bear_risk_triggers=bear_risk_triggers,
    )


def get_prompts_dir(agent_name: str) -> Path:
    """返回指定 agent 的 prompts 目录。"""
    return _BASE_AGENTS / agent_name / "prompts"
