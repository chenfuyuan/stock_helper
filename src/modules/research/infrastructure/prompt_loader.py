"""
技术分析师 Prompt 运行时加载：从资源目录读取 system.md、user.md，不硬编码在代码中。
"""
import json
from pathlib import Path
from typing import Optional

from src.modules.research.domain.indicators_snapshot import TechnicalIndicatorsSnapshot


# 默认资源目录：相对于本文件所在位置定位 technical_analyst/prompts
_DEFAULT_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent / "agents" / "technical_analyst" / "prompts"
)


def load_system_prompt(prompts_dir: Optional[Path] = None) -> str:
    """加载技术分析师 System Prompt。"""
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    path = base / "system.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_user_prompt_template(prompts_dir: Optional[Path] = None) -> str:
    """加载技术分析师 User Prompt 模板（含占位符）。"""
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    path = base / "user.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def fill_user_prompt(
    template: str,
    ticker: str,
    analysis_date: str,
    snapshot: TechnicalIndicatorsSnapshot,
) -> str:
    """用本次调用的 ticker、analysis_date、指标快照填充 User Prompt 占位符。"""
    support_str = json.dumps(snapshot.calculated_support_levels) if snapshot.calculated_support_levels else "[]"
    resistance_str = json.dumps(snapshot.calculated_resistance_levels) if snapshot.calculated_resistance_levels else "[]"
    patterns_str = json.dumps(snapshot.detected_patterns, ensure_ascii=False) if snapshot.detected_patterns else "[]"
    return template.format(
        ticker=ticker,
        analysis_date=analysis_date,
        current_price=snapshot.current_price,
        change_percent=snapshot.change_percent,
        ma5=snapshot.ma5,
        ma20=snapshot.ma20,
        ma60=snapshot.ma60,
        ma200=snapshot.ma200,
        vwap_value=snapshot.vwap_value,
        price_vs_vwap_status=snapshot.price_vs_vwap_status,
        rsi_value=snapshot.rsi_value,
        macd_dif=snapshot.macd_dif,
        macd_dea=snapshot.macd_dea,
        macd_histogram=snapshot.macd_histogram,
        kdj_k=snapshot.kdj_k,
        kdj_d=snapshot.kdj_d,
        bb_upper=snapshot.bb_upper,
        bb_lower=snapshot.bb_lower,
        bb_middle=snapshot.bb_middle,
        bb_bandwidth=snapshot.bb_bandwidth,
        atr_value=snapshot.atr_value,
        volume_ratio=snapshot.volume_ratio,
        obv_trend=snapshot.obv_trend,
        calculated_support_levels=support_str,
        calculated_resistance_levels=resistance_str,
        detected_patterns=patterns_str,
    )


# 财务审计员 Prompt 填充


def load_financial_auditor_system_prompt(prompts_dir: Path) -> str:
    """加载财务审计员 System Prompt。"""
    path = prompts_dir / "system.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_financial_auditor_user_template(prompts_dir: Path) -> str:
    """加载财务审计员 User Prompt 模板（含占位符）。"""
    path = prompts_dir / "user.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def fill_financial_auditor_user_prompt(template: str, snapshot) -> str:
    """用财务快照 DTO 填充 User Prompt 占位符。snapshot 为 FinancialSnapshotDTO。"""
    # 序列需 JSON 序列化以便模板中的 JSON 块正确
    quarter_list = json.dumps(snapshot.quarter_list, ensure_ascii=False)
    revenue_growth_series = json.dumps(
        snapshot.revenue_growth_series, ensure_ascii=False
    )
    profit_growth_series = json.dumps(
        snapshot.profit_growth_series, ensure_ascii=False
    )
    gross_margin_series = json.dumps(
        snapshot.gross_margin_series, ensure_ascii=False
    )
    roic_series = json.dumps(snapshot.roic_series, ensure_ascii=False)
    fcff_series = json.dumps(snapshot.fcff_series, ensure_ascii=False)
    invturn_days_series = json.dumps(
        snapshot.invturn_days_series, ensure_ascii=False
    )
    arturn_days_series = json.dumps(
        snapshot.arturn_days_series, ensure_ascii=False
    )
    return template.format(
        symbol=snapshot.symbol,
        report_period=snapshot.report_period,
        source=snapshot.source,
        gross_margin=snapshot.gross_margin,
        netprofit_margin=snapshot.netprofit_margin,
        roe_waa=snapshot.roe_waa,
        roic=snapshot.roic,
        eps=snapshot.eps,
        eps_deducted=snapshot.eps_deducted,
        ocfps=snapshot.ocfps,
        fcff_ps=snapshot.fcff_ps,
        quality_ratio=snapshot.quality_ratio,
        current_ratio=snapshot.current_ratio,
        quick_ratio=snapshot.quick_ratio,
        debt_to_assets=snapshot.debt_to_assets,
        interestdebt=snapshot.interestdebt,
        netdebt=snapshot.netdebt,
        invturn_days=snapshot.invturn_days,
        arturn_days=snapshot.arturn_days,
        assets_turn=snapshot.assets_turn,
        quarter_list=quarter_list,
        revenue_growth_series=revenue_growth_series,
        profit_growth_series=profit_growth_series,
        gross_margin_series=gross_margin_series,
        roic_series=roic_series,
        fcff_series=fcff_series,
        invturn_days_series=invturn_days_series,
        arturn_days_series=arturn_days_series,
    )
