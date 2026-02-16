"""数据同步服务测试的公共 fixtures。

提供 Service 测试所需的 mock 对象和辅助函数。
"""

from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.domain.model.sync_task import SyncTask


# =============================================================================
# Mock Fixtures for Session and Repository
# =============================================================================


@pytest.fixture
def mock_async_session() -> MagicMock:
    """提供模拟的 AsyncSession。

    Returns:
        配置好的 MagicMock 对象，模拟 AsyncSession 的行为
    """
    session = MagicMock(spec=AsyncSession)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_scheduler_repo() -> MagicMock:
    """提供模拟的 SchedulerExecutionLogRepository。

    Returns:
        配置好的 MagicMock 对象，模拟仓库的行为
    """
    repo = MagicMock()
    repo.__aenter__ = AsyncMock(return_value=repo)
    repo.__aexit__ = AsyncMock(return_value=None)
    return repo


# =============================================================================
# Mock Fixtures for Sync Engine and Factory
# =============================================================================


@pytest.fixture
def mock_sync_engine() -> MagicMock:
    """提供模拟的 SyncEngine。

    Returns:
        配置好的 MagicMock 对象，模拟同步引擎的行为
    """
    engine = MagicMock()
    engine.__aenter__ = AsyncMock(return_value=engine)
    engine.__aexit__ = AsyncMock(return_value=None)

    # 配置常用方法的返回值
    engine.run_incremental_daily_sync = AsyncMock(
        return_value={
            "synced_dates": ["20250215"],
            "total_count": 100,
            "message": "同步成功",
        }
    )
    engine.run_history_sync = AsyncMock(return_value=MagicMock(spec=SyncTask))

    return engine


@pytest.fixture
def mock_sync_use_case_factory() -> Generator[MagicMock, None, None]:
    """提供模拟的 SyncUseCaseFactory。

    Yields:
        配置好的 MagicMock 对象，模拟工厂的行为
    """
    with patch(
        "src.modules.data_engineering.application.services.daily_sync_service.SyncUseCaseFactory"
    ) as mock_factory:
        mock_factory.create_sync_engine = MagicMock()
        yield mock_factory


# =============================================================================
# Mock Fixtures for Execution Tracker
# =============================================================================


@pytest.fixture
def mock_execution_tracker() -> Generator[MagicMock, None, None]:
    """提供模拟的 ExecutionTracker。

    Yields:
        配置好的 MagicMock 对象，模拟执行追踪器的行为
    """
    with patch(
        "src.modules.data_engineering.application.services.base.sync_service_base.ExecutionTracker"
    ) as mock_tracker_class:
        mock_tracker = MagicMock()
        mock_tracker.__aenter__ = AsyncMock(return_value=mock_tracker)
        mock_tracker.__aexit__ = AsyncMock(return_value=None)
        mock_tracker_class.return_value = mock_tracker
        yield mock_tracker_class


# =============================================================================
# Session and Database Fixtures
# =============================================================================


@pytest.fixture
def mock_async_session_local() -> Generator[MagicMock, None, None]:
    """提供模拟的 AsyncSessionLocal。

    Yields:
        配置好的 MagicMock 对象，模拟异步会话工厂的行为
    """
    with patch(
        "src.modules.data_engineering.application.services.base.sync_service_base.AsyncSessionLocal"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory.return_value = mock_session
        yield mock_session_factory


# =============================================================================
# Helper Functions
# =============================================================================


def create_mock_sync_task(
    task_id: str = "test-task-id",
    status: str = "completed",
    total_processed: int = 100,
) -> MagicMock:
    """创建模拟的 SyncTask 对象。

    Args:
        task_id: 任务 ID
        status: 任务状态
        total_processed: 处理的总记录数

    Returns:
        配置好的 MagicMock 对象，模拟 SyncTask 的行为
    """
    task = MagicMock(spec=SyncTask)
    task.id = task_id
    task.status.value = status
    task.total_processed = total_processed
    return task
