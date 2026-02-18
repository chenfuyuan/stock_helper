"""
Prompt 运行时加载：从资源目录读取 system.md、user.md，不硬编码在代码中。
"""

import json
from pathlib import Path
from typing import Optional

# 默认资源目录：相对于本文件定位
_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent / "agents" / "prompts"


def load_system_prompt(prompts_dir: Optional[Path] = None) -> str:
    """加载 System Prompt。"""
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    path = base / "system.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_user_prompt_template(prompts_dir: Optional[Path] = None) -> str:
    """加载 User Prompt 模板（含占位符）。"""
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    path = base / "user.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def fill_user_prompt(
    template: str,
    concepts_list: str,
) -> str:
    """用概念列表填充 User Prompt 占位符。"""
    return template.format(concepts_list=concepts_list)
