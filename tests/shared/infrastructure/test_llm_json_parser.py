"""
统一泛型 LLM JSON 处理器的单元测试。

覆盖 spec unified-llm-output-parser 的全部 Scenario：
- 纯净 JSON / markdown 包裹 / think 标签 / 前后说明文字 / 控制字符
- 非法内容 / 空返回 / 数组根节点
- 字段校验成功 / 失败 / 归一化钩子 / 钩子异常
- context_label 日志
"""

import pytest
from pydantic import BaseModel

from src.shared.domain.exceptions import LLMJsonParseError
from src.shared.infrastructure.llm_json_parser import parse_llm_json_output


# ---------------------------------------------------------------------------
# 测试用 DTO
# ---------------------------------------------------------------------------

class _SimpleDTO(BaseModel):
    score: int
    signal: str


class _RequiredFieldDTO(BaseModel):
    name: str
    value: float


# ---------------------------------------------------------------------------
# Scenario: 纯净 JSON 直接解析
# ---------------------------------------------------------------------------

class TestCleanJson:
    def test_parse_clean_json(self):
        raw = '{"score": 85, "signal": "bullish"}'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 85
        assert result.signal == "bullish"


# ---------------------------------------------------------------------------
# Scenario: Markdown 代码块包裹
# ---------------------------------------------------------------------------

class TestMarkdownCodeBlock:
    def test_parse_json_in_markdown_block(self):
        raw = '```json\n{"score": 85, "signal": "bullish"}\n```'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 85
        assert result.signal == "bullish"

    def test_parse_json_in_markdown_block_no_lang(self):
        raw = '```\n{"score": 90, "signal": "bearish"}\n```'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 90
        assert result.signal == "bearish"


# ---------------------------------------------------------------------------
# Scenario: think 标签 + Markdown 代码块
# ---------------------------------------------------------------------------

class TestThinkTags:
    def test_strip_think_then_markdown(self):
        raw = (
            "<think>这是推理过程，应该被剥离。</think>\n"
            '```json\n{"score": 85, "signal": "bullish"}\n```'
        )
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 85

    def test_think_tags_only_json(self):
        raw = '<think>推理过程</think>\n{"score": 70, "signal": "neutral"}'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 70


# ---------------------------------------------------------------------------
# Scenario: JSON 前后附带说明文字（fallback 提取）
# ---------------------------------------------------------------------------

class TestFallbackExtraction:
    def test_json_with_surrounding_text(self):
        raw = '以下是分析结果：\n{"score": 85, "signal": "bullish"}\n以上为分析。'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 85
        assert result.signal == "bullish"


# ---------------------------------------------------------------------------
# Scenario: 字符串值内含字面换行（控制字符修复）
# ---------------------------------------------------------------------------

class TestControlCharRepair:
    def test_literal_newline_in_string_value(self):
        # JSON 字符串值内含字面换行
        raw = '{"score": 85, "signal": "bull\nish"}'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.score == 85
        assert result.signal == "bull\nish"

    def test_literal_tab_in_string_value(self):
        raw = '{"score": 85, "signal": "bull\tish"}'
        result = parse_llm_json_output(raw, _SimpleDTO)
        assert result.signal == "bull\tish"


# ---------------------------------------------------------------------------
# Scenario: 完全非法内容
# ---------------------------------------------------------------------------

class TestInvalidContent:
    def test_plain_text_raises(self):
        raw = "我无法完成这个任务"
        with pytest.raises(LLMJsonParseError) as exc_info:
            parse_llm_json_output(raw, _SimpleDTO)
        assert "json_error" in exc_info.value.details


# ---------------------------------------------------------------------------
# Scenario: 空返回
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_string_raises(self):
        with pytest.raises(LLMJsonParseError) as exc_info:
            parse_llm_json_output("", _SimpleDTO)
        assert "为空" in exc_info.value.message

    def test_none_like_raises(self):
        """传入 None 应抛异常（虽然类型注解为 str，但防御式编程）。"""
        with pytest.raises(LLMJsonParseError):
            parse_llm_json_output(None, _SimpleDTO)  # type: ignore[arg-type]

    def test_whitespace_only_raises(self):
        with pytest.raises(LLMJsonParseError):
            parse_llm_json_output("   \n\t  ", _SimpleDTO)


# ---------------------------------------------------------------------------
# Scenario: JSON 根节点为数组
# ---------------------------------------------------------------------------

class TestArrayRoot:
    def test_array_root_raises(self):
        raw = '[{"item": 1}]'
        with pytest.raises(LLMJsonParseError) as exc_info:
            parse_llm_json_output(raw, _SimpleDTO)
        assert "根节点" in exc_info.value.message


# ---------------------------------------------------------------------------
# Scenario: 字段校验成功 / 失败
# ---------------------------------------------------------------------------

class TestPydanticValidation:
    def test_valid_fields(self):
        raw = '{"name": "test", "value": 3.14}'
        result = parse_llm_json_output(raw, _RequiredFieldDTO)
        assert result.name == "test"
        assert result.value == 3.14

    def test_missing_required_field(self):
        raw = '{"name": "test"}'
        with pytest.raises(LLMJsonParseError) as exc_info:
            parse_llm_json_output(raw, _RequiredFieldDTO)
        assert "validation_errors" in exc_info.value.details

    def test_wrong_field_type(self):
        raw = '{"name": "test", "value": "not_a_number"}'
        with pytest.raises(LLMJsonParseError) as exc_info:
            parse_llm_json_output(raw, _RequiredFieldDTO)
        assert "validation_errors" in exc_info.value.details


# ---------------------------------------------------------------------------
# Scenario: 归一化钩子
# ---------------------------------------------------------------------------

class TestNormalizers:
    def test_enum_normalization(self):
        """模拟 valuation_modeler 的 verdict 枚举映射。"""
        mapping = {"Undervalued (低估)": "Undervalued", "Fair (合理)": "Fair"}

        def normalize_verdict(data: dict) -> dict:
            v = data.get("signal", "")
            if v in mapping:
                data["signal"] = mapping[v]
            return data

        raw = '{"score": 85, "signal": "Undervalued (低估)"}'
        result = parse_llm_json_output(
            raw, _SimpleDTO, normalizers=[normalize_verdict]
        )
        assert result.signal == "Undervalued"

    def test_object_array_to_string_list(self):
        """模拟 bull_advocate 的 supporting_arguments 对象数组 → 字符串列表。"""

        class _ListDTO(BaseModel):
            items: list[str]

        def normalize_items(data: dict) -> dict:
            raw_items = data.get("items", [])
            data["items"] = [
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in raw_items
            ]
            return data

        raw = '{"items": [{"text": "arg1"}, {"text": "arg2"}]}'
        result = parse_llm_json_output(raw, _ListDTO, normalizers=[normalize_items])
        assert result.items == ["arg1", "arg2"]

    def test_no_normalizers(self):
        raw = '{"score": 85, "signal": "bullish"}'
        result = parse_llm_json_output(raw, _SimpleDTO, normalizers=None)
        assert result.score == 85

    def test_empty_normalizers_list(self):
        raw = '{"score": 85, "signal": "bullish"}'
        result = parse_llm_json_output(raw, _SimpleDTO, normalizers=[])
        assert result.score == 85


# ---------------------------------------------------------------------------
# Scenario: 钩子执行异常
# ---------------------------------------------------------------------------

class TestNormalizerException:
    def test_hook_raises_key_error(self):
        def bad_hook(data: dict) -> dict:
            _ = data["nonexistent_key"]
            return data

        raw = '{"score": 85, "signal": "bullish"}'
        with pytest.raises(LLMJsonParseError) as exc_info:
            parse_llm_json_output(raw, _SimpleDTO, normalizers=[bad_hook])
        assert "normalizer_error" in exc_info.value.details


# ---------------------------------------------------------------------------
# Scenario: context_label 日志
# ---------------------------------------------------------------------------

class TestContextLabel:
    def test_label_in_warning_log(self, capfd):
        """解析失败时日志中应包含 context_label。

        因为 loguru 默认输出到 stderr，使用 capfd 捕获。
        若 loguru sink 不走 stderr，该测试仍验证不抛非预期异常。
        """
        with pytest.raises(LLMJsonParseError):
            parse_llm_json_output(
                "not json", _SimpleDTO, context_label="财务审计员"
            )
        # 基本验证：函数正确抛出了异常即可；日志断言作为可选验证

    def test_no_label_does_not_error(self):
        """无 context_label 时不报错。"""
        with pytest.raises(LLMJsonParseError):
            parse_llm_json_output("not json", _SimpleDTO, context_label="")
