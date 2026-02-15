"""测试 Foundation 模块 Scheduler 领域异常

对应规格：openspec/changes/refactor-scheduler-to-foundation/specs/foundation-scheduler-service/spec.md

验证目标：
- Scheduler 异常从 shared 迁移到 Foundation 模块
- 所有异常类继承自 src.shared.domain.exceptions.AppException
- 异常类包含正确的 code、status_code 和语义化的 message
- 各异常类符合预期的构造器签名
"""

import pytest

from src.shared.domain.exceptions import AppException
from src.modules.foundation.domain.exceptions import (
    SchedulerException,
    SchedulerJobNotFoundException,
    SchedulerJobAlreadyExistsException,
    SchedulerConfigurationException,
    SchedulerExecutionException,
)


class TestSchedulerExceptions:
    """测试 Scheduler 异常体系"""

    def test_scheduler_exception_inherits_from_app_exception(self):
        """验证 SchedulerException 继承自 AppException"""
        assert issubclass(SchedulerException, AppException)

    def test_scheduler_exception_default_values(self):
        """验证 SchedulerException 默认值"""
        exc = SchedulerException("测试消息")
        assert exc.message == "测试消息"
        assert exc.code == "SCHEDULER_ERROR"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_scheduler_exception_custom_values(self):
        """验证 SchedulerException 可自定义 code 和 status_code"""
        exc = SchedulerException(
            message="自定义消息",
            code="CUSTOM_SCHEDULER_ERROR",
            status_code=503,
            details={"key": "value"}
        )
        assert exc.message == "自定义消息"
        assert exc.code == "CUSTOM_SCHEDULER_ERROR"
        assert exc.status_code == 503
        assert exc.details == {"key": "value"}

    def test_job_not_found_exception(self):
        """验证 SchedulerJobNotFoundException"""
        exc = SchedulerJobNotFoundException("test_job_123")
        
        assert isinstance(exc, SchedulerException)
        assert isinstance(exc, AppException)
        assert exc.job_id == "test_job_123"
        assert "test_job_123" in exc.message
        assert exc.code == "SCHEDULER_JOB_NOT_FOUND"
        assert exc.status_code == 404

    def test_job_already_exists_exception(self):
        """验证 SchedulerJobAlreadyExistsException"""
        exc = SchedulerJobAlreadyExistsException("duplicate_job")
        
        assert isinstance(exc, SchedulerException)
        assert isinstance(exc, AppException)
        assert exc.job_id == "duplicate_job"
        assert "duplicate_job" in exc.message
        assert exc.code == "SCHEDULER_JOB_ALREADY_EXISTS"
        assert exc.status_code == 409

    def test_configuration_exception(self):
        """验证 SchedulerConfigurationException"""
        exc = SchedulerConfigurationException(
            config_key="max_workers",
            config_value=-1,
            reason="值必须为正整数"
        )
        
        assert isinstance(exc, SchedulerException)
        assert isinstance(exc, AppException)
        assert exc.config_key == "max_workers"
        assert exc.config_value == -1
        assert exc.reason == "值必须为正整数"
        assert "max_workers" in exc.message
        assert exc.code == "SCHEDULER_CONFIG_ERROR"
        assert exc.status_code == 400

    def test_execution_exception(self):
        """验证 SchedulerExecutionException"""
        original_error = ValueError("原始错误")
        exc = SchedulerExecutionException(
            job_id="failed_job",
            error_message="任务执行失败",
            original_error=original_error
        )
        
        assert isinstance(exc, SchedulerException)
        assert isinstance(exc, AppException)
        assert exc.job_id == "failed_job"
        assert exc.error_message == "任务执行失败"
        assert exc.original_error is original_error
        assert "failed_job" in exc.message
        assert exc.code == "SCHEDULER_EXECUTION_ERROR"
        assert exc.status_code == 500

    def test_execution_exception_without_job_id(self):
        """验证 SchedulerExecutionException 允许 job_id 为 None"""
        exc = SchedulerExecutionException(
            job_id=None,
            error_message="调度器初始化失败"
        )
        
        assert exc.job_id is None
        assert exc.error_message == "调度器初始化失败"
        assert exc.original_error is None
        assert exc.code == "SCHEDULER_EXECUTION_ERROR"
        assert exc.status_code == 500
