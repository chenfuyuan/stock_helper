"""APScheduler 适配器集成测试

测试 APScheduler 适配器与实际调度器的集成功能。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.modules.foundation.infrastructure.adapters.apscheduler_adapter import APSchedulerAdapter
from src.modules.foundation.domain.exceptions import (
    SchedulerJobNotFoundException,
    SchedulerJobAlreadyExistsException,
    SchedulerExecutionException
)


class TestAPSchedulerAdapterIntegration:
    """测试 APScheduler 适配器集成功能"""

    @pytest.fixture
    async def adapter(self):
        """创建适配器实例"""
        adapter = APSchedulerAdapter()
        await adapter.start_scheduler()
        yield adapter
        await adapter.shutdown_scheduler()

    @pytest.fixture
    def sample_job_func(self):
        """示例任务函数"""
        async def sample_job(param1=None, param2=None):
            """示例任务"""
            return f"executed with {param1}, {param2}"
        return sample_job

    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self, adapter):
        """测试适配器生命周期"""
        # 测试启动状态（在 fixture 中已经启动）
        # APScheduler 不提供 is_initialized/is_running 方法
        # 我们通过操作来验证状态
        
        # 测试停止和重新启动
        await adapter.shutdown_scheduler()
        await adapter.start_scheduler()

    @pytest.mark.asyncio
    async def test_schedule_and_get_job(self, adapter, sample_job_func):
        """测试调度和获取任务"""
        # 调度任务
        await adapter.schedule_job(
            job_id="test_job",
            job_func=sample_job_func,
            cron_expression="0 9 * * 1-5",
            timezone="UTC",
            param1="value1",
            param2="value2"
        )
        
        # 获取任务状态
        job_status = await adapter.get_job_status("test_job")
        assert job_status is not None
        assert job_status["id"] == "test_job"

    @pytest.mark.asyncio
    async def test_schedule_duplicate_job(self, adapter, sample_job_func):
        """测试调度重复任务"""
        # 第一次调度
        await adapter.schedule_job(
            job_id="duplicate_job",
            job_func=sample_job_func,
            cron_expression="0 9 * * 1-5"
        )
        
        # 第二次调度应该抛出异常
        with pytest.raises(SchedulerJobAlreadyExistsException):
            await adapter.schedule_job(
                job_id="duplicate_job",
                job_func=sample_job_func,
                cron_expression="0 10 * * 1-5"
            )

    @pytest.mark.asyncio
    async def test_remove_job(self, adapter, sample_job_func):
        """测试移除任务"""
        # 调度任务
        await adapter.schedule_job(
            job_id="removable_job",
            job_func=sample_job_func,
            cron_expression="0 9 * * 1-5"
        )
        
        # 确认任务存在
        job_status = await adapter.get_job_status("removable_job")
        assert job_status is not None
        assert job_status["id"] == "removable_job"
        
        # 移除任务
        await adapter.remove_job("removable_job")
        
        # 确认任务不存在
        job_status = await adapter.get_job_status("removable_job")
        assert job_status is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_job(self, adapter):
        """测试移除不存在的任务"""
        with pytest.raises(SchedulerJobNotFoundException):
            await adapter.remove_job("nonexistent_job")

    @pytest.mark.asyncio
    async def test_trigger_job(self, adapter, sample_job_func):
        """测试触发任务"""
        # 调度任务
        await adapter.schedule_job(
            job_id="triggerable_job",
            job_func=sample_job_func,
            cron_expression="0 9 * * 1-5"
        )
        
        # 触发任务（注意：实际执行可能需要等待）
        await adapter.trigger_job("triggerable_job")

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_job(self, adapter):
        """测试触发不存在的任务"""
        with pytest.raises(SchedulerJobNotFoundException):
            await adapter.trigger_job("nonexistent_job")

    @pytest.mark.asyncio
    async def test_get_all_jobs(self, adapter, sample_job_func):
        """测试获取所有任务"""
        # 调度多个任务
        jobs_data = [
            ("job1", "0 8 * * 1-5"),
            ("job2", "0 9 * * 1-5"),
            ("job3", "0 10 * * 1-5")
        ]
        
        for job_id, cron_expr in jobs_data:
            await adapter.schedule_job(
                job_id=job_id,
                job_func=sample_job_func,
                cron_expression=cron_expr
            )
        
        # 获取所有任务
        all_jobs = await adapter.get_all_jobs()
        assert len(all_jobs) >= 3
        
        job_ids = [job["id"] for job in all_jobs]
        for job_id, _ in jobs_data:
            assert job_id in job_ids


    @pytest.mark.asyncio
    async def test_schedule_job_with_invalid_cron(self, adapter, sample_job_func):
        """测试调度无效 Cron 表达式的任务"""
        with pytest.raises(SchedulerExecutionException):
            await adapter.schedule_job(
                job_id="invalid_cron_job",
                job_func=sample_job_func,
                cron_expression="invalid cron expression"
            )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, adapter, sample_job_func):
        """测试并发操作"""
        # 并发调度多个任务
        tasks = []
        for i in range(5):
            task = adapter.schedule_job(
                job_id=f"concurrent_job_{i}",
                job_func=sample_job_func,
                cron_expression=f"0 {8+i} * * 1-5"
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # 验证所有任务都被调度
        all_jobs = await adapter.get_all_jobs()
        job_ids = [job["id"] for job in all_jobs]
        
        for i in range(5):
            assert f"concurrent_job_{i}" in job_ids
