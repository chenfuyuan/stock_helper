"""
单元测试：配置外部化（任务 9.7）
"""
import pytest
import os

from src.shared.config import Settings


def test_sync_config_defaults():
    """测试同步相关配置的默认值"""
    settings = Settings()
    
    # 验证所有新增配置项的默认值
    assert settings.SYNC_DAILY_HISTORY_BATCH_SIZE == 50
    assert settings.SYNC_FINANCE_HISTORY_BATCH_SIZE == 100
    assert settings.SYNC_FINANCE_HISTORY_START_DATE == "20200101"
    assert settings.SYNC_INCREMENTAL_MISSING_LIMIT == 300
    assert settings.SYNC_FAILURE_MAX_RETRIES == 3
    assert settings.TUSHARE_MIN_INTERVAL == 0.35


def test_sync_config_from_environment():
    """测试通过环境变量覆盖同步配置"""
    # 设置环境变量
    os.environ["SYNC_DAILY_HISTORY_BATCH_SIZE"] = "100"
    os.environ["SYNC_FINANCE_HISTORY_BATCH_SIZE"] = "200"
    os.environ["SYNC_FINANCE_HISTORY_START_DATE"] = "20150101"
    os.environ["SYNC_INCREMENTAL_MISSING_LIMIT"] = "500"
    os.environ["SYNC_FAILURE_MAX_RETRIES"] = "5"
    os.environ["TUSHARE_MIN_INTERVAL"] = "0.5"
    
    try:
        settings = Settings()
        
        # 验证环境变量覆盖生效
        assert settings.SYNC_DAILY_HISTORY_BATCH_SIZE == 100
        assert settings.SYNC_FINANCE_HISTORY_BATCH_SIZE == 200
        assert settings.SYNC_FINANCE_HISTORY_START_DATE == "20150101"
        assert settings.SYNC_INCREMENTAL_MISSING_LIMIT == 500
        assert settings.SYNC_FAILURE_MAX_RETRIES == 5
        assert settings.TUSHARE_MIN_INTERVAL == 0.5
    finally:
        # 清理环境变量
        for key in [
            "SYNC_DAILY_HISTORY_BATCH_SIZE",
            "SYNC_FINANCE_HISTORY_BATCH_SIZE",
            "SYNC_FINANCE_HISTORY_START_DATE",
            "SYNC_INCREMENTAL_MISSING_LIMIT",
            "SYNC_FAILURE_MAX_RETRIES",
            "TUSHARE_MIN_INTERVAL",
        ]:
            os.environ.pop(key, None)


def test_tushare_min_interval_config():
    """测试 Tushare 限速配置可配置化"""
    # 默认值
    settings = Settings()
    assert settings.TUSHARE_MIN_INTERVAL == 0.35
    
    # 环境变量覆盖
    os.environ["TUSHARE_MIN_INTERVAL"] = "0.4"
    try:
        settings = Settings()
        assert settings.TUSHARE_MIN_INTERVAL == 0.4
    finally:
        os.environ.pop("TUSHARE_MIN_INTERVAL", None)
