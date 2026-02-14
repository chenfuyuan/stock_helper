"""
单元测试：配置外部化与模块化。
Shared Settings 仅保留全局配置；Tushare/同步配置在 DataEngineeringConfig，LLM/博查在 LLMPlatformConfig。
"""

import os

from src.modules.data_engineering.infrastructure.config import (
    DataEngineeringConfig,
)
from src.modules.llm_platform.infrastructure.config import LLMPlatformConfig
from src.shared.config import Settings


def test_shared_config_global_only():
    """Shared Settings 仅含全局配置，不含 TUSHARE_/SYNC_/LLM_/BOCHA_。"""
    settings = Settings()
    assert settings.PROJECT_NAME == "Stock Helper"
    assert settings.API_V1_STR == "/api/v1"
    assert hasattr(settings, "POSTGRES_SERVER")
    assert not hasattr(settings, "TUSHARE_MIN_INTERVAL")
    assert not hasattr(settings, "SYNC_DAILY_HISTORY_BATCH_SIZE")
    assert not hasattr(settings, "LLM_API_KEY")


def test_de_config_defaults():
    """数据工程模块配置默认值。"""
    de = DataEngineeringConfig()
    assert de.SYNC_DAILY_HISTORY_BATCH_SIZE == 50
    assert de.SYNC_FINANCE_HISTORY_BATCH_SIZE == 100
    assert de.SYNC_FINANCE_HISTORY_START_DATE == "20200101"
    assert de.SYNC_INCREMENTAL_MISSING_LIMIT == 300
    assert de.SYNC_FAILURE_MAX_RETRIES == 3
    assert de.TUSHARE_MIN_INTERVAL == 0.35


def test_de_config_from_environment():
    """数据工程配置可从环境变量覆盖。"""
    os.environ["SYNC_DAILY_HISTORY_BATCH_SIZE"] = "100"
    os.environ["TUSHARE_MIN_INTERVAL"] = "0.5"
    try:
        de = DataEngineeringConfig()
        assert de.SYNC_DAILY_HISTORY_BATCH_SIZE == 100
        assert de.TUSHARE_MIN_INTERVAL == 0.5
    finally:
        os.environ.pop("SYNC_DAILY_HISTORY_BATCH_SIZE", None)
        os.environ.pop("TUSHARE_MIN_INTERVAL", None)


def test_llm_config_defaults():
    """LLM 平台模块配置默认值。"""
    llm = LLMPlatformConfig()
    assert llm.LLM_PROVIDER == "openai"
    assert llm.LLM_MODEL == "gpt-3.5-turbo"
    assert hasattr(llm, "BOCHA_BASE_URL")
