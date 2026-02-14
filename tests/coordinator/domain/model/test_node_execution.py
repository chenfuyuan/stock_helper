"""
任务 12.3：测试 NodeExecution 成功记录与失败记录。
"""

from datetime import datetime, timezone
from uuid import uuid4

from src.modules.coordinator.domain.model.node_execution import NodeExecution


def test_mark_success_sets_result_and_clears_error():
    """mark_success() 写入 result_data、narrative_report，并清空 error 字段。"""
    started_at = datetime.now(timezone.utc)
    execution = NodeExecution(
        id=uuid4(),
        session_id=uuid4(),
        node_type="technical_analyst",
        status="success",
        started_at=started_at,
        error_type="SomeError",
        error_message="before",
    )
    completed_at = started_at.replace(microsecond=0)
    duration_ms = 1000
    result_data = {"signal": "BULLISH", "confidence": 0.8}
    narrative_report = "技术面偏多。"

    execution.mark_success(
        result_data=result_data,
        narrative_report=narrative_report,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )

    assert execution.status == "success"
    assert execution.result_data == result_data
    assert execution.narrative_report == narrative_report
    assert execution.completed_at == completed_at
    assert execution.duration_ms == duration_ms
    assert execution.error_type is None
    assert execution.error_message is None


def test_mark_success_empty_narrative_report_stored_as_none():
    """mark_success(..., narrative_report="") 将 narrative_report 存为 None。"""
    started_at = datetime.now(timezone.utc)
    execution = NodeExecution(
        id=uuid4(),
        session_id=uuid4(),
        node_type="financial_auditor",
        started_at=started_at,
    )
    completed_at = started_at.replace(microsecond=0)
    execution.mark_success(
        result_data={},
        narrative_report="",
        completed_at=completed_at,
        duration_ms=0,
    )
    assert execution.narrative_report is None


def test_mark_failed_sets_error_and_clears_result():
    """mark_failed() 写入 error_type、error_message，并清空 result_data、narrative_report。"""
    started_at = datetime.now(timezone.utc)
    execution = NodeExecution(
        id=uuid4(),
        session_id=uuid4(),
        node_type="judge",
        status="success",
        started_at=started_at,
        result_data={"verdict": "BUY"},
        narrative_report="看多",
    )
    completed_at = started_at.replace(microsecond=0)
    duration_ms = 50

    execution.mark_failed(
        error_type="ValueError",
        error_message="解析失败",
        completed_at=completed_at,
        duration_ms=duration_ms,
    )

    assert execution.status == "failed"
    assert execution.error_type == "ValueError"
    assert execution.error_message == "解析失败"
    assert execution.completed_at == completed_at
    assert execution.duration_ms == duration_ms
    assert execution.result_data is None
    assert execution.narrative_report is None
