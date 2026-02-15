"""测试 SchedulerPort 接口完整性

对应规格：openspec/changes/refactor-scheduler-to-foundation/specs/foundation-scheduler-service/spec.md

验证目标：
- SchedulerPort 包含所有必需的抽象方法（7个）
- remove_job() 和 trigger_job() 已补充到 Port 接口中（消除 hasattr hack）
- 所有方法均为抽象方法，确保实现类必须提供完整实现
"""

import inspect
from abc import ABCMeta
from typing import get_type_hints

import pytest

from src.modules.foundation.domain.ports.scheduler_port import SchedulerPort


class TestSchedulerPortInterface:
    """测试 SchedulerPort 接口定义"""

    def test_is_abstract_base_class(self):
        """验证 SchedulerPort 是抽象基类"""
        assert isinstance(SchedulerPort, ABCMeta)

    def test_has_schedule_job_method(self):
        """验证 schedule_job 方法存在且为抽象方法"""
        assert hasattr(SchedulerPort, "schedule_job")
        assert getattr(SchedulerPort.schedule_job, "__isabstractmethod__", False)

    def test_has_start_scheduler_method(self):
        """验证 start_scheduler 方法存在且为抽象方法"""
        assert hasattr(SchedulerPort, "start_scheduler")
        assert getattr(SchedulerPort.start_scheduler, "__isabstractmethod__", False)

    def test_has_shutdown_scheduler_method(self):
        """验证 shutdown_scheduler 方法存在且为抽象方法"""
        assert hasattr(SchedulerPort, "shutdown_scheduler")
        assert getattr(SchedulerPort.shutdown_scheduler, "__isabstractmethod__", False)

    def test_has_get_job_status_method(self):
        """验证 get_job_status 方法存在且为抽象方法"""
        assert hasattr(SchedulerPort, "get_job_status")
        assert getattr(SchedulerPort.get_job_status, "__isabstractmethod__", False)

    def test_has_get_all_jobs_method(self):
        """验证 get_all_jobs 方法存在且为抽象方法"""
        assert hasattr(SchedulerPort, "get_all_jobs")
        assert getattr(SchedulerPort.get_all_jobs, "__isabstractmethod__", False)

    def test_has_remove_job_method(self):
        """验证 remove_job 方法存在且为抽象方法（补全缺失的 Port 定义）"""
        assert hasattr(SchedulerPort, "remove_job"), \
            "remove_job 方法应在 Port 接口中定义，消除 Application Service 中的 hasattr hack"
        assert getattr(SchedulerPort.remove_job, "__isabstractmethod__", False), \
            "remove_job 必须是抽象方法"

    def test_has_trigger_job_method(self):
        """验证 trigger_job 方法存在且为抽象方法（补全缺失的 Port 定义）"""
        assert hasattr(SchedulerPort, "trigger_job"), \
            "trigger_job 方法应在 Port 接口中定义，支持手动触发任务"
        assert getattr(SchedulerPort.trigger_job, "__isabstractmethod__", False), \
            "trigger_job 必须是抽象方法"

    def test_all_methods_count(self):
        """验证 Port 接口包含 7 个抽象方法"""
        abstract_methods = [
            name for name, method in inspect.getmembers(SchedulerPort, predicate=inspect.isfunction)
            if getattr(method, "__isabstractmethod__", False)
        ]
        assert len(abstract_methods) == 7, \
            f"SchedulerPort 应包含 7 个抽象方法，实际: {len(abstract_methods)} 个 {abstract_methods}"

    def test_cannot_instantiate_directly(self):
        """验证无法直接实例化 Port 接口"""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SchedulerPort()  # type: ignore

    def test_remove_job_signature(self):
        """验证 remove_job 方法签名符合预期"""
        method = getattr(SchedulerPort, "remove_job")
        sig = inspect.signature(method)
        
        # 检查参数：self, job_id
        params = list(sig.parameters.keys())
        assert "job_id" in params, "remove_job 应接受 job_id 参数"

    def test_trigger_job_signature(self):
        """验证 trigger_job 方法签名符合预期"""
        method = getattr(SchedulerPort, "trigger_job")
        sig = inspect.signature(method)
        
        # 检查参数：self, job_id, 可能还有 **kwargs
        params = list(sig.parameters.keys())
        assert "job_id" in params, "trigger_job 应接受 job_id 参数"
