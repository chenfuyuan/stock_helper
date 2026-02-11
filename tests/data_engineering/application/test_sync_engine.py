"""
单元测试：SyncEngine 核心功能（任务 9.2-9.4）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.modules.data_engineering.application.commands.sync_engine import SyncEngine
from src.modules.data_engineering.domain.model.sync_task import SyncTask
from src.modules.data_engineering.domain.model.enums import SyncJobType, SyncTaskStatus


@pytest.fixture
def mock_repositories():
    """创建 mock 的 repositories 和 providers"""
    return {
        "sync_task_repo": AsyncMock(),
        "stock_repo": AsyncMock(),
        "daily_repo": AsyncMock(),
        "finance_repo": AsyncMock(),
        "quote_provider": AsyncMock(),
        "finance_provider": AsyncMock(),
    }


@pytest.fixture
def sync_engine(mock_repositories):
    """创建 SyncEngine 实例"""
    return SyncEngine(
        sync_task_repo=mock_repositories["sync_task_repo"],
        stock_repo=mock_repositories["stock_repo"],
        daily_repo=mock_repositories["daily_repo"],
        finance_repo=mock_repositories["finance_repo"],
        quote_provider=mock_repositories["quote_provider"],
        finance_provider=mock_repositories["finance_provider"],
    )


@pytest.mark.asyncio
async def test_sync_engine_creates_new_task_when_none_exists(sync_engine, mock_repositories):
    """测试 SyncEngine 创建新任务（任务 9.2 的一部分）"""
    # Mock: 没有已存在的任务
    mock_repositories["sync_task_repo"].get_latest_by_job_type.return_value = None
    
    # Mock: 创建任务返回新任务
    new_task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
    )
    mock_repositories["sync_task_repo"].create.return_value = new_task
    
    # Mock: 每批返回 0，立即完成
    with patch.object(sync_engine, '_execute_batch', new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"synced_stocks": 0}
        
        result = await sync_engine.run_history_sync(
            job_type=SyncJobType.DAILY_HISTORY,
            config={"batch_size": 50}
        )
    
    # 验证：创建了新任务
    mock_repositories["sync_task_repo"].create.assert_called_once()
    
    # 验证：任务最终状态为 COMPLETED
    assert result.status == SyncTaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_engine_rejects_when_running_task_exists(sync_engine, mock_repositories):
    """测试 SyncEngine 同类型任务互斥（任务 9.3）"""
    # Mock: 已存在 RUNNING 状态的同类型任务
    existing_task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.RUNNING,
        batch_size=50,
    )
    mock_repositories["sync_task_repo"].get_latest_by_job_type.return_value = existing_task
    
    result = await sync_engine.run_history_sync(
        job_type=SyncJobType.DAILY_HISTORY,
        config={"batch_size": 50}
    )
    
    # 验证：返回已存在的任务
    assert result == existing_task
    assert result.status == SyncTaskStatus.RUNNING
    
    # 验证：没有创建新任务
    mock_repositories["sync_task_repo"].create.assert_not_called()


@pytest.mark.asyncio
async def test_sync_engine_resumes_paused_task(sync_engine, mock_repositories):
    """测试 SyncEngine 断点续跑（任务 9.4）"""
    # Mock: 已存在 PAUSED 状态的任务（offset=100）
    paused_task = SyncTask(
        job_type=SyncJobType.DAILY_HISTORY,
        status=SyncTaskStatus.PAUSED,
        batch_size=50,
        current_offset=100,
        total_processed=100,
    )
    mock_repositories["sync_task_repo"].get_latest_by_job_type.return_value = paused_task
    mock_repositories["sync_task_repo"].update.return_value = paused_task
    
    # Mock: 下一批返回 0，完成
    with patch.object(sync_engine, '_execute_batch', new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"synced_stocks": 0}
        
        result = await sync_engine.run_history_sync(
            job_type=SyncJobType.DAILY_HISTORY,
            config={"batch_size": 50}
        )
    
    # 验证：从 offset=100 恢复
    assert result.current_offset == 100
    
    # 验证：没有创建新任务
    mock_repositories["sync_task_repo"].create.assert_not_called()
    
    # 验证：更新了任务（启动 + 完成）
    assert mock_repositories["sync_task_repo"].update.call_count >= 2
