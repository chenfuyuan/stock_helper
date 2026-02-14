"""
研究模块内 LLM 输出的通用预处理。

用于各 Agent 的 output_parser：剥离 <think> 标签、剥离 Markdown 代码块，
使「裸 JSON」或「```json ... ```」或「前后有多余文字」的响应都能得到可解析的片段。
并可选地修复字符串值内的未转义控制字符（如字面换行），以通过 json.loads。
"""
import re


def strip_thinking_tags(text: str) -> str:
    """
    移除 reasoning model 输出的 <think>...</think> 标签及其内容。
    部分思考模型（如 DeepSeek R1）会在响应前输出推理过程，需剥离后再解析 JSON。
    """
    if not text or "<think>" not in text:
        return text
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def strip_markdown_code_block(text: str) -> str:
    """
    剥离 Markdown 代码块（```json 或 ``` 包裹的内容）。
    不要求闭合 ``` 紧贴行尾，允许末尾有空白或多余字符，按「首个开块到最后一个闭块」取内容。
    """
    stripped = (text or "").strip()
    if not stripped.startswith("```"):
        return stripped
    first = stripped.find("```")
    last = stripped.rfind("```")
    if last <= first:
        return stripped
    content = stripped[first + 3 : last].strip()
    if content.lower().startswith("json"):
        content = content[4:].lstrip("\r\n\t ")
    return content.strip()


def _repair_control_chars_in_json_strings(text: str) -> str:
    """
    在 JSON 字符串值内部，将未转义的控制字符（换行、回车、制表等）转为转义形式。
    JSON 不允许字符串内出现字面 \\n/\\r/\\t 等，LLM 常直接输出换行导致解析失败。
    """
    result: list[str] = []
    i = 0
    in_string = False
    escape = False
    quote_char: str | None = None
    while i < len(text):
        c = text[i]
        if not in_string:
            result.append(c)
            if c in ('"', "'"):
                in_string = True
                quote_char = c
            i += 1
            continue
        if escape:
            result.append(c)
            escape = False
            i += 1
            continue
        if c == "\\":
            result.append(c)
            escape = True
            i += 1
            continue
        if c == quote_char:
            result.append(c)
            in_string = False
            quote_char = None
            i += 1
            continue
        if c == "\n":
            result.append("\\n")
        elif c == "\r":
            result.append("\\r")
        elif c == "\t":
            result.append("\\t")
        elif ord(c) < 32 and c != " ":
            result.append("\\u%04x" % ord(c))
        else:
            result.append(c)
        i += 1
    return "".join(result)


def normalize_llm_json_like_text(raw: str, repair_control_chars: bool = True) -> str:
    """
    对「疑似 JSON 的 LLM 文本」做标准化：先剥 <think>，再剥代码块；
    若 repair_control_chars 为 True，再修复字符串值内的未转义控制字符（换行等）。
    各 Agent 的 output_parser 可在解析前调用此函数，再 json.loads。
    """
    if not raw or not raw.strip():
        return raw.strip() if raw else ""
    text = raw.strip()
    text = strip_thinking_tags(text)
    text = strip_markdown_code_block(text)
    if repair_control_chars:
        text = _repair_control_chars_in_json_strings(text)
    return text
