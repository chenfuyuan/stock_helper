"""
宏观情报员 Agent 的 LLM 输出解析。

将本 Agent 返回的 JSON 字符串解析为 MacroIntelligenceResultDTO，内聚于该 Agent。
非法 JSON 或缺字段时记录日志（含 LLM 原始输出，便于排查）并抛出 LLMOutputParseError。
"""
import json
import re
from typing import Any, Union

from loguru import logger
from pydantic import ValidationError

from src.modules.research.domain.dtos.macro_dtos import MacroIntelligenceResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError

_RAW_LOG_MAX_LEN = 2000


def _raw_for_log(raw: str) -> str:
    """返回用于日志的原始内容，过长时截断。"""
    if not raw:
        return "(空)"
    s = raw.strip()
    if len(s) <= _RAW_LOG_MAX_LEN:
        return s
    return s[:_RAW_LOG_MAX_LEN] + f"...[已截断，总长 {len(s)} 字符]"


def _strip_thinking_tags(text: str) -> str:
    """
    移除 reasoning model 输出的 <think>...</think> 标签及其内容。
    
    部分思考模型（如 DeepSeek R1）会在响应前输出推理过程，需剥离后才能解析 JSON。
    """
    if "<think>" in text:
        # 移除所有 <think>...</think> 块（支持嵌套或多次出现）
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text


def _format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """将 Pydantic 校验错误格式化为可读摘要。"""
    parts = []
    for err in errors:
        loc = ".".join(str(x) for x in err.get("loc", ()))
        msg = err.get("msg", "")
        inp = err.get("input")
        if inp is None:
            actual = "None/缺失"
        elif isinstance(inp, list):
            actual = f"list (长度 {len(inp)})"
        elif isinstance(inp, dict):
            actual = f"dict (键: {list(inp.keys())[:5]})"
        else:
            actual = f"{type(inp).__name__} ({repr(inp)[:50]})"
        parts.append(f"字段 {loc}：{msg}，实际：{actual}")
    return "；".join(parts)


def parse_macro_intelligence_result(raw: str) -> MacroIntelligenceResultDTO:
    """
    将宏观情报员 LLM 返回的字符串解析为 MacroIntelligenceResultDTO。
    
    处理流程：
    1. 剥离 <think>...</think> 标签（reasoning model 的思考过程）
    2. 剥离 Markdown 代码块（```json ... ``` 或 ``` ... ```）
    3. 解析 JSON
    4. 用 Pydantic 校验并反序列化为 MacroIntelligenceResultDTO
    
    非法 JSON 或校验失败时记录日志（含 LLM 原始输出）并抛出 LLMOutputParseError。
    
    Args:
        raw: LLM 原始返回字符串
        
    Returns:
        MacroIntelligenceResultDTO: 解析后的宏观分析结果
        
    Raises:
        LLMOutputParseError: 解析失败时（空内容、非法 JSON、字段校验失败）
    """
    if not raw or not raw.strip():
        logger.warning(
            "解析宏观情报结果：LLM 返回为空，raw={}", _raw_for_log(raw or "")
        )
        raise LLMOutputParseError(
            message="LLM 返回内容为空", details={"raw_length": 0}
        )

    text = raw.strip()
    
    # 1. 移除 reasoning model 的 <think>...</think> 标签
    text = _strip_thinking_tags(text)
    
    # 2. 剥离 Markdown 代码块
    match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # 3. 解析 JSON
    try:
        data: Union[dict, list] = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            "解析宏观情报结果：非合法 JSON，msg={}，LLM 原始输出：{}",
            e.msg,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": e.msg, "position": e.pos},
        ) from e

    if not isinstance(data, dict):
        logger.warning(
            "解析宏观情报结果：JSON 根节点非对象，LLM 原始输出：{}",
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回 JSON 根节点须为对象", details={}
        )

    data.setdefault("narrative_report", "")
    # 4. 用 Pydantic 校验并反序列化
    try:
        dto = MacroIntelligenceResultDTO.model_validate(data)
    except ValidationError as e:
        summary = _format_validation_errors(e.errors())
        logger.warning(
            "解析宏观情报结果：字段校验失败。详情：{} | LLM 原始输出：{}",
            summary,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合宏观情报结果契约：{summary}",
            details={"validation_errors": e.errors(), "summary": summary},
        ) from e

    logger.info(
        "宏观情报结果解析成功：macro_environment={}，confidence_score={}，"
        "维度分析数={}，机会数={}，风险数={}，来源数={}",
        dto.macro_environment,
        dto.confidence_score,
        len(dto.dimension_analyses),
        len(dto.key_opportunities),
        len(dto.key_risks),
        len(dto.information_sources),
    )

    return dto
