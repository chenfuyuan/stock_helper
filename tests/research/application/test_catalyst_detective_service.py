import pytest
from unittest.mock import AsyncMock, Mock

from src.modules.research.application.catalyst_detective_service import CatalystDetectiveService
from src.modules.research.domain.ports.catalyst_data import ICatalystDataPort
from src.modules.research.domain.ports.catalyst_context_builder import ICatalystContextBuilder
from src.modules.research.domain.ports.catalyst_detective_agent import ICatalystDetectiveAgentPort
from src.modules.research.domain.dtos.catalyst_inputs import (
    CatalystStockOverview,
    CatalystSearchResult,
    CatalystSearchResultItem,
)
from src.modules.research.domain.dtos.catalyst_context import CatalystContextDTO
from src.modules.research.domain.dtos.catalyst_dtos import CatalystDetectiveAgentResult, CatalystDetectiveResultDTO
from src.modules.research.domain.exceptions import StockNotFoundError, CatalystSearchError
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
    data_port.get_stock_overview = AsyncMock(return_value=CatalystStockOverview(
        stock_name="Test", industry="Ind", third_code="Code"
    ))
    data_port.search_catalyst_context = AsyncMock(return_value=[
        CatalystSearchResult(
            dimension_topic="Topic",
            items=[CatalystSearchResultItem(title="T", url="u", snippet="s")],
        )
    ])

    # Mock context builder
    context_dto = CatalystContextDTO(
        stock_name="Test", third_code="Code", industry="Ind", current_date="2023",
        company_events_context="C", industry_catalyst_context="I", market_sentiment_context="M", earnings_context="E", all_source_urls="U"
    )
    context_builder.build.return_value = context_dto

    # Mock agent
    agent_result = CatalystDetectiveAgentResult(
        result=Mock(spec=CatalystDetectiveResultDTO),
        raw_llm_output="raw",
        user_prompt="prompt",
        catalyst_context=context_dto,
    )
    agent_port.analyze = AsyncMock(return_value=agent_result)

    res = await service.run("TestSymbol")

    assert res == agent_result
    data_port.get_stock_overview.assert_called_with("TestSymbol")
    agent_port.analyze.assert_called_with("TestSymbol", context_dto)


@pytest.mark.asyncio
async def test_stock_not_found(mock_pipeline):
    service, data_port, _, _ = mock_pipeline
    data_port.get_stock_overview = AsyncMock(return_value=None)

    with pytest.raises(StockNotFoundError):
        await service.run("Invalid")


@pytest.mark.asyncio
async def test_search_failed_all_empty(mock_pipeline):
    service, data_port, _, _ = mock_pipeline
    data_port.get_stock_overview = AsyncMock(return_value=CatalystStockOverview(
        stock_name="Test", industry="Ind", third_code="Code"
    ))
    # Return empty items for all dimensions
    data_port.search_catalyst_context = AsyncMock(return_value=[
        CatalystSearchResult(dimension_topic="Topic", items=[])
    ])

    with pytest.raises(CatalystSearchError):
        await service.run("TestSymbol")


@pytest.mark.asyncio
async def test_empty_symbol(mock_pipeline):
    service, _, _, _ = mock_pipeline
    with pytest.raises(BadRequestException):
        await service.run("")
