"""
Coordinator 测试 fixtures：mock IResearchExpertGateway 等。
"""

from unittest.mock import AsyncMock

import pytest

from src.modules.coordinator.domain.model.enums import ExpertType
from src.modules.coordinator.domain.ports.research_expert_gateway import (
    IResearchExpertGateway,
)


@pytest.fixture
def mock_research_expert_gateway():
    """Mock IResearchExpertGateway，默认所有专家返回成功。"""
    gateway = AsyncMock(spec=IResearchExpertGateway)
    gateway.run_expert = AsyncMock(return_value={"signal": "NEUTRAL", "confidence": 0.8})
    return gateway


@pytest.fixture
def mock_gateway_with_failure():
    """Mock Gateway：technical_analyst 抛异常，其余成功。"""
    gateway = AsyncMock(spec=IResearchExpertGateway)
    success_result = {"signal": "NEUTRAL", "confidence": 0.8}

    async def run_expert(expert_type, symbol, options=None):
        if expert_type == ExpertType.TECHNICAL_ANALYST:
            raise ValueError("技术分析师执行失败")
        return success_result

    gateway.run_expert = run_expert
    return gateway


@pytest.fixture
def mock_gateway_all_fail():
    """Mock Gateway：全部专家抛异常。"""
    gateway = AsyncMock(spec=IResearchExpertGateway)
    gateway.run_expert = AsyncMock(side_effect=RuntimeError("专家执行失败"))
    return gateway
