"""调度器领域 DTO 测试

测试调度器相关的数据传输对象，确保数据校验和序列化功能正常。
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.modules.foundation.domain.dtos.scheduler_dtos import (
    JobStatus,
    JobConfigDTO,
    JobStatusDTO,
    JobExecutionDTO,
    SchedulerConfigDTO,
)


class TestJobStatus:
    """测试 JobStatus 枚举"""

    def test_job_status_values(self):
        """测试任务状态枚举值"""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.SUCCESS == "success"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"

    def test_job_status_is_string(self):
        """测试任务状态是字符串类型"""
        assert isinstance(JobStatus.PENDING, str)
        assert isinstance(JobStatus.RUNNING, str)


class TestJobConfigDTO:
    """测试 JobConfigDTO"""

    def test_valid_job_config(self):
        """测试有效的任务配置"""
        config = JobConfigDTO(
            job_id="test_job",
            job_name="测试任务",
            cron_expression="0 9 * * 1-5",
            timezone="UTC",
            enabled=True,
            job_kwargs={"param1": "value1"}
        )
        
        assert config.job_id == "test_job"
        assert config.job_name == "测试任务"
        assert config.cron_expression == "0 9 * * 1-5"
        assert config.timezone == "UTC"
        assert config.enabled is True
        assert config.job_kwargs == {"param1": "value1"}

    def test_job_config_defaults(self):
        """测试任务配置默认值"""
        config = JobConfigDTO(
            job_id="test_job",
            job_name="测试任务",
            cron_expression="0 9 * * 1-5"
        )
        
        assert config.timezone == "UTC"
        assert config.enabled is True
        assert config.job_kwargs == {}

    def test_invalid_cron_expression_too_few_parts(self):
        """测试无效的 Cron 表达式 - 部分太少"""
        with pytest.raises(ValidationError, match="Cron 表达式必须包含 5 或 6 个部分"):
            JobConfigDTO(
                job_id="test_job",
                job_name="测试任务",
                cron_expression="0 9 * *"
            )

    def test_invalid_cron_expression_too_many_parts(self):
        """测试无效的 Cron 表达式 - 部分太多"""
        with pytest.raises(ValidationError, match="无效的 cron 表达式部分"):
            JobConfigDTO(
                job_id="test_job",
                job_name="测试任务",
                cron_expression="0 9 * * 1-5 extra"
            )

    def test_invalid_cron_expression_invalid_chars(self):
        """测试无效的 Cron 表达式 - 无效字符"""
        with pytest.raises(ValidationError, match="无效的 cron 表达式部分"):
            JobConfigDTO(
                job_id="test_job",
                job_name="测试任务",
                cron_expression="0 9 * * 1-5 @"
            )

    def test_valid_cron_expressions(self):
        """测试有效的 Cron 表达式"""
        valid_expressions = [
            "0 9 * * 1-5",  # 工作日 9 点
            "*/5 * * * *",  # 每 5 分钟
            "0 0 1 * *",   # 每月 1 日零点
            "0 0 * * 0",   # 每周日零点
            "0 9 * * 1-5",  # 5 位表达式
            "0 9 * * 1-5 2023",  # 6 位表达式（年份）
        ]
        
        for expr in valid_expressions:
            config = JobConfigDTO(
                job_id="test_job",
                job_name="测试任务",
                cron_expression=expr
            )
            assert config.cron_expression == expr

    def test_invalid_timezone(self):
        """测试无效的时区"""
        with pytest.raises(ValidationError, match="不支持的时区"):
            JobConfigDTO(
                job_id="test_job",
                job_name="测试任务",
                cron_expression="0 9 * * 1-5",
                timezone="Invalid/Timezone"
            )

    def test_valid_timezones(self):
        """测试有效的时区"""
        valid_timezones = ['UTC', 'Asia/Shanghai', 'Asia/Tokyo', 'America/New_York']
        
        for tz in valid_timezones:
            config = JobConfigDTO(
                job_id="test_job",
                job_name="测试任务",
                cron_expression="0 9 * * 1-5",
                timezone=tz
            )
            assert config.timezone == tz

    def test_empty_job_id(self):
        """测试空的任务 ID"""
        with pytest.raises(ValidationError, match="job_id"):
            JobConfigDTO(
                job_id="",
                job_name="测试任务",
                cron_expression="0 9 * * 1-5"
            )

    def test_empty_job_name(self):
        """测试空的任务名称"""
        with pytest.raises(ValidationError, match="job_name"):
            JobConfigDTO(
                job_id="test_job",
                job_name="",
                cron_expression="0 9 * * 1-5"
            )


class TestJobStatusDTO:
    """测试 JobStatusDTO"""

    def test_valid_job_status(self):
        """测试有效的任务状态"""
        now = datetime.now()
        future = now + timedelta(hours=1)
        
        status = JobStatusDTO(
            job_id="test_job",
            job_name="测试任务",
            is_running=True,
            next_run_time=future,
            trigger_description="每日 9 点执行",
            job_kwargs={"param1": "value1"}
        )
        
        assert status.job_id == "test_job"
        assert status.job_name == "测试任务"
        assert status.is_running is True
        assert status.next_run_time == future
        assert status.trigger_description == "每日 9 点执行"
        assert status.job_kwargs == {"param1": "value1"}

    def test_job_status_defaults(self):
        """测试任务状态默认值"""
        status = JobStatusDTO(
            job_id="test_job",
            job_name="测试任务"
        )
        
        assert status.is_running is False
        assert status.next_run_time is None
        assert status.trigger_description is None
        assert status.job_kwargs == {}

    def test_invalid_next_run_time_past(self):
        """测试无效的下次运行时间 - 过去时间"""
        past = datetime.now() - timedelta(hours=1)
        
        with pytest.raises(ValidationError, match="下次运行时间不能是过去的时间"):
            JobStatusDTO(
                job_id="test_job",
                job_name="测试任务",
                next_run_time=past
            )

    def test_valid_next_run_time_future(self):
        """测试有效的下次运行时间 - 未来时间"""
        future = datetime.now() + timedelta(hours=1)
        
        status = JobStatusDTO(
            job_id="test_job",
            job_name="测试任务",
            next_run_time=future
        )
        assert status.next_run_time == future

    def test_valid_next_run_time_none(self):
        """测试有效的下次运行时间 - 空值"""
        status = JobStatusDTO(
            job_id="test_job",
            job_name="测试任务",
            next_run_time=None
        )
        assert status.next_run_time is None


class TestJobExecutionDTO:
    """测试 JobExecutionDTO"""

    def test_valid_job_execution_success(self):
        """测试有效的任务执行记录 - 成功"""
        started = datetime.now()
        finished = started + timedelta(minutes=5)
        
        execution = JobExecutionDTO(
            job_id="test_job",
            started_at=started,
            finished_at=finished,
            status=JobStatus.SUCCESS,
            duration_ms=300000
        )
        
        assert execution.job_id == "test_job"
        assert execution.started_at == started
        assert execution.finished_at == finished
        assert execution.status == JobStatus.SUCCESS
        assert execution.duration_ms == 300000
        assert execution.error_message is None

    def test_valid_job_execution_failed(self):
        """测试有效的任务执行记录 - 失败"""
        started = datetime.now()
        
        execution = JobExecutionDTO(
            job_id="test_job",
            started_at=started,
            status=JobStatus.FAILED,
            error_message="任务执行失败：连接超时"
        )
        
        assert execution.status == JobStatus.FAILED
        assert execution.error_message == "任务执行失败：连接超时"
        assert execution.finished_at is None
        assert execution.duration_ms is None

    def test_invalid_finished_at_before_started(self):
        """测试无效的结束时间 - 早于开始时间"""
        started = datetime.now()
        finished = started - timedelta(minutes=1)
        
        with pytest.raises(ValidationError, match="结束时间不能早于开始时间"):
            JobExecutionDTO(
                job_id="test_job",
                started_at=started,
                finished_at=finished,
                status=JobStatus.SUCCESS
            )

    def test_invalid_duration_negative(self):
        """测试无效的持续时间 - 负数"""
        with pytest.raises(ValidationError, match="Input should be greater than or equal to 0"):
            JobExecutionDTO(
                job_id="test_job",
                started_at=datetime.now(),
                status=JobStatus.SUCCESS,
                duration_ms=-1000
            )

    def test_invalid_error_message_with_success(self):
        """测试无效的错误信息 - 成功状态"""
        with pytest.raises(ValidationError, match="成功状态不能有错误信息"):
            JobExecutionDTO(
                job_id="test_job",
                started_at=datetime.now(),
                status=JobStatus.SUCCESS,
                error_message="不应该有错误信息"
            )

    def test_valid_error_message_with_failed(self):
        """测试有效的错误信息 - 失败状态"""
        execution = JobExecutionDTO(
            job_id="test_job",
            started_at=datetime.now(),
            status=JobStatus.FAILED,
            error_message="任务执行失败"
        )
        assert execution.error_message == "任务执行失败"

    def test_valid_zero_duration(self):
        """测试有效的零持续时间"""
        execution = JobExecutionDTO(
            job_id="test_job",
            started_at=datetime.now(),
            finished_at=datetime.now(),
            status=JobStatus.SUCCESS,
            duration_ms=0
        )
        assert execution.duration_ms == 0


class TestSchedulerConfigDTO:
    """测试 SchedulerConfigDTO"""

    def test_valid_scheduler_config(self):
        """测试有效的调度器配置"""
        config = SchedulerConfigDTO(
            timezone="Asia/Shanghai",
            max_workers=10,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
                "timezone": "UTC"
            }
        )
        
        assert config.timezone == "Asia/Shanghai"
        assert config.max_workers == 10
        assert config.job_defaults["coalesce"] is True
        assert config.job_defaults["max_instances"] == 1

    def test_scheduler_config_defaults(self):
        """测试调度器配置默认值"""
        config = SchedulerConfigDTO()
        
        assert config.timezone == "UTC"
        assert config.max_workers == 5
        assert config.job_defaults == {}

    def test_invalid_timezone(self):
        """测试无效的时区"""
        with pytest.raises(ValidationError, match="不支持的时区"):
            SchedulerConfigDTO(timezone="Invalid/Timezone")

    def test_invalid_max_workers_too_low(self):
        """测试无效的最大工作线程数 - 太小"""
        with pytest.raises(ValidationError, match="max_workers"):
            SchedulerConfigDTO(max_workers=0)

    def test_invalid_max_workers_too_high(self):
        """测试无效的最大工作线程数 - 太大"""
        with pytest.raises(ValidationError, match="max_workers"):
            SchedulerConfigDTO(max_workers=21)

    def test_valid_max_workers_range(self):
        """测试有效的最大工作线程数范围"""
        for workers in [1, 5, 10, 20]:
            config = SchedulerConfigDTO(max_workers=workers)
            assert config.max_workers == workers

    def test_invalid_job_defaults_key(self):
        """测试无效的任务默认配置键"""
        with pytest.raises(ValidationError, match="不支持的任务配置项"):
            SchedulerConfigDTO(
                job_defaults={"invalid_key": "value"}
            )

    def test_valid_job_defaults_keys(self):
        """测试有效的任务默认配置键"""
        valid_configs = [
            {"coalesce": True},
            {"max_instances": 1},
            {"misfire_grace_time": 300},
            {"timezone": "UTC"},
            {"coalesce": True, "max_instances": 1},
        ]
        
        for config in valid_configs:
            scheduler_config = SchedulerConfigDTO(job_defaults=config)
            assert scheduler_config.job_defaults == config

    def test_mixed_valid_job_defaults(self):
        """测试混合的有效任务默认配置"""
        config = SchedulerConfigDTO(
            job_defaults={
                "coalesce": False,
                "max_instances": 3,
                "misfire_grace_time": 600,
                "timezone": "Asia/Shanghai"
            }
        )
        
        assert config.job_defaults["coalesce"] is False
        assert config.job_defaults["max_instances"] == 3
        assert config.job_defaults["misfire_grace_time"] == 600
        assert config.job_defaults["timezone"] == "Asia/Shanghai"
