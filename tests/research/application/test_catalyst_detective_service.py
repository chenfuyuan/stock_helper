from unittest.mock import AsyncMock, Mock

import pytest

from src.modules.research.application.catalyst_detective_service import (
    CatalystDetectiveService,
)
from src.modules.research.domain.dtos.catalyst_context import (
    CatalystContextDTO,
)
from src.modules.research.domain.dtos.catalyst_dtos import (
    CatalystDetectiveAgentResult,
    CatalystDetectiveResultDTO,
)
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystSearchResult,
    CatalystSearchResultItem,
    CatalystStockOverview,
)
from src.modules.research.domain.ports.catalyst_context_builder import (
    ICatalystContextBuilder,
)
from src.modules.research.domain.ports.catalyst_data import ICatalystDataPort
from src.modules.research.domain.ports.catalyst_detective_agent import (
    ICatalystDetectiveAgentPort,
)
from src.shared.domain.exceptions import BadRequestException


@pytest.fixture
def mock_pipeline():
    data_port = Mock(spec=ICatalystDataPort)
    context_builder = Mock(spec=ICatalystContextBuilder)
    agent_port = Mock(spec=ICatalystDetectiveAgentPort)
    service = CatalystDetectiveService(data_port, context_builder, agent_port)
    return service, data_port, context_builder, agent_port


@pytest.mark.asyncio
async def test_run_success(mock_pipeline):
    service, data_port, context_builder, agent_port = mock_pipeline

    # Mock data port
    data_port.get_stock_overview = AsyncMock(
        return_value=CatalystStockOverview(
            stock_name="Test", industry="Ind", third_code="Code"
        )
    )
    data_port.search_catalyst_context = AsyncMock(
        return_value=[
            CatalystSearchResult(
                dimension_topic="Topic",
                items=[
                    CatalystSearchResultItem(title="T", url="u", snippet="s")
                ],
            )
        ]
    )

    # Mock context builder
    context_dto = CatalystContextDTO(
        stock_name="Test",
        third_code="Code",
        industry="Ind",
        current_date="2023",
        company_events_context="C",
        industry_catalyst_context="I",
        market_sentiment_context="M",
        earnings_context="E",
        all_source_urls="U",
    )
    context_builder.build.return_value = context_dto

    # Mock agent（run() 内部会调用 result.model_dump() 与 catalyst_context.model_dump()）
    result_dto = Mock(spec=CatalystDetectiveResultDTO)
    result_dto.model_dump.return_value = {
        "catalyst_assessment": "Neutral (中性)",
        "confidence_score": 0.5,
        "catalyst_summary": "",
        "dimension_analyses": [],
        "positive_catalysts": [],
        "negative_catalysts": [],
        "information_sources": [],
        "narrative_report": "",
    }
    agent_result = CatalystDetectiveAgentResult(
        result=result_dto,
        raw_llm_output="raw",
        user_prompt="prompt",
        catalyst_context=context_dto,
    )
    agent_port.analyze = AsyncMock(return_value=agent_result)

    res = await service.run("TestSymbol")

    assert isinstance(res, dict)
    assert "result" in res and isinstance(res["result"], dict)
    assert res["raw_llm_output"] == "raw"
    assert res["user_prompt"] == "prompt"
    assert "catalyst_context" in res
    data_port.get_stock_overview.assert_called_with("TestSymbol")
    agent_port.analyze.assert_called_with("TestSymbol", context_dto)


@pytest.mark.asyncio
async def test_stock_not_found_raises_bad_request(mock_pipeline):
    service, data_port, _, _ = mock_pipeline
    data_port.get_stock_overview = AsyncMock(return_value=None)

    with pytest.raises(BadRequestException) as exc_info:
        await service.run("Invalid")
    assert (
        "不存在" in exc_info.value.message
        or "Invalid" in exc_info.value.message
    )


@pytest.mark.asyncio
async def test_search_failed_all_empty_raises_bad_request(mock_pipeline):
    service, data_port, _, _ = mock_pipeline
    data_port.get_stock_overview = AsyncMock(
        return_value=CatalystStockOverview(
            stock_name="Test", industry="Ind", third_code="Code"
        )
    )
    data_port.search_catalyst_context = AsyncMock(
        return_value=[
            CatalystSearchResult(dimension_topic="Topic", items=[]),
        ]
    )

    with pytest.raises(BadRequestException) as exc_info:
        await service.run("TestSymbol")
    assert (
        "搜索" in exc_info.value.message
        or "失败" in exc_info.value.message
        or "无结果" in exc_info.value.message
    )


@pytest.mark.asyncio
async def test_empty_symbol(mock_pipeline):
    service, _, _, _ = mock_pipeline
    with pytest.raises(BadRequestException):
        await service.run("")
