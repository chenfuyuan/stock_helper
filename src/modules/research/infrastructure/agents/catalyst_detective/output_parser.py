import json
import re
import logging
from typing import Any, Union

from pydantic import ValidationError

from src.modules.research.domain.dtos.catalyst_dtos import CatalystDetectiveResultDTO
from src.modules.research.domain.exceptions import LLMOutputParseError

logger = logging.getLogger(__name__)

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
    """
    if "<think>" in text:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text


def parse_catalyst_detective_result(raw: str) -> CatalystDetectiveResultDTO:
    """
    将催化剂侦探 LLM 返回的字符串解析为 CatalystDetectiveResultDTO。
    """
    if not raw or not raw.strip():
        logger.warning(
            f"解析催化剂侦探结果：LLM 返回为空，raw={_raw_for_log(raw or '')}"
        )
        raise LLMOutputParseError(
            message="LLM 返回内容为空", details={"raw_length": 0}
        )

    text = raw.strip()
    
    # 1. 移除 reasoning model 的 <think>...<think> 标签
    text = _strip_thinking_tags(text)

    # 2. 剥离 Markdown 代码块
    # 使用与宏观情报员相同的正则，支持 json 标识或无标识
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    
    # 也尝试直接去掉头尾的 ``` 如果正则没匹配到但确实存在
    if text.startswith("```") and text.endswith("```"):
         text = text.strip("`").strip()

    # 3. 解析 JSON
    try:
        data: Union[dict, list] = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            f"解析催化剂侦探结果：非合法 JSON，msg={e.msg}，LLM 原始输出：{_raw_for_log(raw)}"
        )
        raise LLMOutputParseError(
            message="LLM 返回内容不是合法 JSON",
            details={"json_error": e.msg, "position": e.pos},
        ) from e

    if not isinstance(data, dict):
        logger.warning(
            f"解析催化剂侦探结果：JSON 根节点非对象，LLM 原始输出：{_raw_for_log(raw)}"
        )
        raise LLMOutputParseError(
            message="LLM 返回 JSON 根节点须为对象", details={}
        )

    # 4. 用 Pydantic 校验并反序列化
    try:
        dto = CatalystDetectiveResultDTO.model_validate(data)
    except ValidationError as e:
        logger.warning(
            f"解析催化剂侦探结果：字段校验失败。LLM 原始输出：{_raw_for_log(raw)}"
        )
        raise LLMOutputParseError(
            message=f"LLM 返回格式不符合催化剂侦探结果契约",
            details={"validation_errors": e.errors()},
        ) from e

    logger.info(
        f"催化剂侦探结果解析成功：catalyst_assessment={dto.catalyst_assessment}，confidence_score={dto.confidence_score}，"
        f"正面催化数={len(dto.positive_catalysts)}，负面催化数={len(dto.negative_catalysts)}，来源数={len(dto.information_sources)}"
    )

    return dto
