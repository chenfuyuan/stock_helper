"""
Judge Prompt 运行时加载。

从 agents/verdict/prompts 读取 system.md、user.md，提供 load_system_prompt、
load_user_prompt_template、fill_user_prompt 等工具函数（复用 Debate 模式）。
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


def fill_user_prompt(
    template: str,
    symbol: str,
    direction: str,
    confidence: float,
    bull_thesis: str,
    bear_thesis: str,
    risk_factors: str,
    key_disagreements: str,
    conflict_resolution: str,
) -> str:
    """填充裁决者 user prompt 占位符。"""
    return template.format(
        symbol=symbol,
        direction=direction,
        confidence=confidence,
        bull_thesis=bull_thesis,
        bear_thesis=bear_thesis,
        risk_factors=risk_factors,
        key_disagreements=key_disagreements,
        conflict_resolution=conflict_resolution,
    )


def get_prompts_dir(agent_name: str) -> Path:
    """返回指定 agent 的 prompts 目录。"""
    return _BASE_AGENTS / agent_name / "prompts"
