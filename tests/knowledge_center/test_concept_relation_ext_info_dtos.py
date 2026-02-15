"""
概念关系扩展信息 DTO 单元测试。

测试 ManualExtInfo 和 LLMExtInfo 的 Pydantic 校验逻辑。
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.modules.knowledge_center.domain.dtos.concept_relation_ext_info_dtos import (
    LLMExtInfo,
    ManualExtInfo,
)


class TestManualExtInfo:
    """手动关系扩展信息测试类。"""

    def test_minimal_creation(self):
        """测试最小字段创建。"""
        ext_info = ManualExtInfo()
        assert ext_info.note is None
        assert ext_info.reason is None

    def test_full_creation(self):
        """测试完整字段创建。"""
        note = "测试备注"
        reason = "测试原因"
        ext_info = ManualExtInfo(note=note, reason=reason)
        assert ext_info.note == note
        assert ext_info.reason == reason

    def test_partial_creation(self):
        """测试部分字段创建。"""
        # 只有 note
        ext_info = ManualExtInfo(note="只有备注")
        assert ext_info.note == "只有备注"
        assert ext_info.reason is None

        # 只有 reason
        ext_info = ManualExtInfo(reason="只有原因")
        assert ext_info.note is None
        assert ext_info.reason == "只有原因"

    def test_string_fields_validation(self):
        """测试字符串字段验证。"""
        # 空字符串应该被接受
        ext_info = ManualExtInfo(note="", reason="")
        assert ext_info.note == ""
        assert ext_info.reason == ""

        # 长字符串应该被接受
        long_text = "a" * 1000
        ext_info = ManualExtInfo(note=long_text, reason=long_text)
        assert ext_info.note == long_text
        assert ext_info.reason == long_text

    def test_serialization(self):
        """测试序列化。"""
        ext_info = ManualExtInfo(note="备注", reason="原因")
        data = ext_info.model_dump()
        assert data == {"note": "备注", "reason": "原因"}

        # 排除 None 值
        data = ext_info.model_dump(exclude_none=True)
        assert data == {"note": "备注", "reason": "原因"}

        ext_info = ManualExtInfo(note="备注")
        data = ext_info.model_dump(exclude_none=True)
        assert data == {"note": "备注"}


class TestLLMExtInfo:
    """LLM 关系扩展信息测试类。"""

    def test_minimal_creation(self):
        """测试最小必填字段创建。"""
        model = "gpt-4"
        prompt = "测试 prompt"
        raw_output = "测试输出"
        parsed_result = {"test": "result"}
        reasoning = "测试推理"
        analyzed_at = datetime.now()

        ext_info = LLMExtInfo(
            model=model,
            prompt=prompt,
            raw_output=raw_output,
            parsed_result=parsed_result,
            reasoning=reasoning,
            analyzed_at=analyzed_at,
        )

        assert ext_info.model == model
        assert ext_info.prompt == prompt
        assert ext_info.raw_output == raw_output
        assert ext_info.parsed_result == parsed_result
        assert ext_info.reasoning == reasoning
        assert ext_info.analyzed_at == analyzed_at
        assert ext_info.model_version is None
        assert ext_info.batch_id is None

    def test_full_creation(self):
        """测试完整字段创建。"""
        model = "gpt-4"
        model_version = "v1.0"
        prompt = "测试 prompt"
        raw_output = "测试输出"
        parsed_result = {"test": "result"}
        reasoning = "测试推理"
        batch_id = "batch_123"
        analyzed_at = datetime.now()

        ext_info = LLMExtInfo(
            model=model,
            model_version=model_version,
            prompt=prompt,
            raw_output=raw_output,
            parsed_result=parsed_result,
            reasoning=reasoning,
            batch_id=batch_id,
            analyzed_at=analyzed_at,
        )

        assert ext_info.model == model
        assert ext_info.model_version == model_version
        assert ext_info.prompt == prompt
        assert ext_info.raw_output == raw_output
        assert ext_info.parsed_result == parsed_result
        assert ext_info.reasoning == reasoning
        assert ext_info.batch_id == batch_id
        assert ext_info.analyzed_at == analyzed_at

    def test_required_fields_validation(self):
        """测试必填字段验证。"""
        # 缺少必填字段应该抛出 ValidationError
        with pytest.raises(ValidationError):
            LLMExtInfo()

        with pytest.raises(ValidationError):
            LLMExtInfo(model="gpt-4")

        with pytest.raises(ValidationError):
            LLMExtInfo(model="gpt-4", prompt="prompt")

        with pytest.raises(ValidationError):
            LLMExtInfo(model="gpt-4", prompt="prompt", raw_output="output")

        with pytest.raises(ValidationError):
            LLMExtInfo(
                model="gpt-4",
                prompt="prompt",
                raw_output="output",
                parsed_result={"test": "result"},
            )

        with pytest.raises(ValidationError):
            LLMExtInfo(
                model="gpt-4",
                prompt="prompt",
                raw_output="output",
                parsed_result={"test": "result"},
                reasoning="reasoning",
            )

    def test_datetime_validation(self):
        """测试时间字段验证。"""
        now = datetime.now()
        
        # 有效 datetime
        ext_info = LLMExtInfo(
            model="gpt-4",
            prompt="prompt",
            raw_output="output",
            parsed_result={"test": "result"},
            reasoning="reasoning",
            analyzed_at=now,
        )
        assert ext_info.analyzed_at == now

        # Pydantic V2 会自动转换有效的日期时间字符串
        ext_info_from_str = LLMExtInfo(
            model="gpt-4",
            prompt="prompt",
            raw_output="output",
            parsed_result={"test": "result"},
            reasoning="reasoning",
            analyzed_at="2023-01-01T00:00:00",  # 字符串会被转换为 datetime
        )
        assert isinstance(ext_info_from_str.analyzed_at, datetime)

        # 无效时间格式
        with pytest.raises(ValidationError):
            LLMExtInfo(
                model="gpt-4",
                prompt="prompt",
                raw_output="output",
                parsed_result={"test": "result"},
                reasoning="reasoning",
                analyzed_at="invalid_datetime",  # 无效格式
            )

    def test_parsed_result_flexibility(self):
        """测试 parsed_result 字段灵活性。"""
        # 可以接受任意 dict 结构
        simple_result = {"relation": "IS_UPSTREAM_OF"}
        complex_result = {
            "relations": [
                {"source": "A", "target": "B", "type": "IS_UPSTREAM_OF"},
                {"source": "B", "target": "C", "type": "IS_DOWNSTREAM_OF"},
            ],
            "confidence": 0.8,
        }

        ext_info1 = LLMExtInfo(
            model="gpt-4",
            prompt="prompt",
            raw_output="output",
            parsed_result=simple_result,
            reasoning="reasoning",
            analyzed_at=datetime.now(),
        )
        assert ext_info1.parsed_result == simple_result

        ext_info2 = LLMExtInfo(
            model="gpt-4",
            prompt="prompt",
            raw_output="output",
            parsed_result=complex_result,
            reasoning="reasoning",
            analyzed_at=datetime.now(),
        )
        assert ext_info2.parsed_result == complex_result

    def test_serialization(self):
        """测试序列化。"""
        analyzed_at = datetime.now()
        ext_info = LLMExtInfo(
            model="gpt-4",
            model_version="v1.0",
            prompt="测试 prompt",
            raw_output="测试输出",
            parsed_result={"test": "result"},
            reasoning="测试推理",
            batch_id="batch_123",
            analyzed_at=analyzed_at,
        )

        data = ext_info.model_dump()
        assert data["model"] == "gpt-4"
        assert data["model_version"] == "v1.0"
        assert data["prompt"] == "测试 prompt"
        assert data["raw_output"] == "测试输出"
        assert data["parsed_result"] == {"test": "result"}
        assert data["reasoning"] == "测试推理"
        assert data["batch_id"] == "batch_123"
        assert "analyzed_at" in data  # datetime 会被序列化为字符串

        # 排除 None 值
        ext_info_partial = LLMExtInfo(
            model="gpt-4",
            prompt="prompt",
            raw_output="output",
            parsed_result={"test": "result"},
            reasoning="reasoning",
            analyzed_at=analyzed_at,
        )
        data = ext_info_partial.model_dump(exclude_none=True)
        assert "model_version" not in data
        assert "batch_id" not in data

    def test_long_content_handling(self):
        """测试长内容处理。"""
        long_prompt = "a" * 10000
        long_output = "b" * 10000
        long_reasoning = "c" * 5000

        ext_info = LLMExtInfo(
            model="gpt-4",
            prompt=long_prompt,
            raw_output=long_output,
            parsed_result={"test": "result"},
            reasoning=long_reasoning,
            analyzed_at=datetime.now(),
        )

        assert len(ext_info.prompt) == 10000
        assert len(ext_info.raw_output) == 10000
        assert len(ext_info.reasoning) == 5000
