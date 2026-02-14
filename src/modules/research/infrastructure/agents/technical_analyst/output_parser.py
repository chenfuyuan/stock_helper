"""
技术分析师 Agent 的 LLM 输出解析。
将本 Agent 返回的 JSON 字符串解析为 TechnicalAnalysisResultDTO，内聚于该 Agent，
其他 Agent 可有各自的输出格式与解析逻辑。
非法 JSON 或缺字段时记录日志（含 LLM 原始输出，便于排查）并抛出 LLMOutputParseError。
"""
import json
import re
from typing import Any, Union

from loguru import logger
from pydantic import ValidationError

from src.modules.research.domain.dtos.technical_analysis_dtos import TechnicalAnalysisResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError

# 日志中打印 LLM 原始输出时的最大长度，避免日志过长
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
        logger.debug("检测到 <think> 标签，正在剥离 reasoning model 的思考过程")
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


def _strip_markdown_code_block(text: str) -> str:
    """
    剥离 Markdown 代码块（```json 或 ``` 包裹的内容）。
    不要求闭合 ``` 紧贴行尾，允许末尾有空白或多余字符，按「首个开块到最后一个闭块」取内容。
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    first_backtick = stripped.find("```")
    last_backtick = stripped.rfind("```")
    if last_backtick <= first_backtick:
        return stripped
    content = stripped[first_backtick + 3 : last_backtick].strip()
    if content.lower().startswith("json"):
        content = content[4:].lstrip("\r\n\t ")
    return content.strip()


def _format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """
    将 Pydantic 校验错误格式化为可读摘要，便于定位问题。
    例如：key_technical_levels.support 期望 float，实际为 list (空数组)。
    """
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


def parse_technical_analysis_result(raw: str) -> TechnicalAnalysisResultDTO:
    """
    将技术分析师 LLM 返回的字符串解析为 TechnicalAnalysisResultDTO。
    若为 Markdown 代码块包裹的 JSON，先剥离再解析。
    非法 JSON 或校验失败时记录日志（含 LLM 原始输出）并抛出 LLMOutputParseError。
    """
    if not raw or not raw.strip():
        logger.warning("解析技术分析结果：LLM 返回为空，raw={}", _raw_for_log(raw or ""))
        raise LLMOutputParseError(message="LLM 返回内容为空", details={"raw_length": 0})

    text = raw.strip()
    # 移除 reasoning model 的 <think>...</think> 标签
    text = _strip_thinking_tags(text)
    # 剥离 ```json ... ``` 或 ``` ... ```（允许末尾有额外字符）
    text = _strip_markdown_code_block(text)

    try:
        data: Union[dict, list] = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            "解析技术分析结果：非合法 JSON，msg={}，LLM 原始输出：{}",
            e.msg,
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": e.msg, "position": e.pos},
        ) from e

    if not isinstance(data, dict):
        logger.warning(
            "解析技术分析结果：JSON 根节点非对象，LLM 原始输出：{}",
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(message="LLM 返回 JSON 根节点须为对象", details={})

    data.setdefault("narrative_report", "")
    try:
        return TechnicalAnalysisResultDTO.model_validate(data)
    except ValidationError as e:
        summary = _format_validation_errors(e.errors())
        logger.warning(
            "解析技术分析结果：字段校验失败。详情：{} | 原始 errors={} | LLM 原始输出：{}",
            summary,
            e.errors(),
            _raw_for_log(raw),
        )
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合技术分析结果契约：{summary}",
            details={"validation_errors": e.errors(), "summary": summary},
        ) from e
