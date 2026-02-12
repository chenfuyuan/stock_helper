"""
估值建模师 REST 接口。
提供按标的进行估值建模的 HTTP 入口；响应体由代码塞入 input、valuation_indicators、output。
"""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import BadRequestException
from src.shared.infrastructure.db.session import get_db_session
from src.modules.research.application.valuation_modeler_service import (
    ValuationModelerService,
)
from src.modules.research.domain.exceptions import LLMOutputParseError

# data_engineering：查询用例
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import (
    StockRepositoryImpl,
)
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import (
    StockDailyRepositoryImpl,
)
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import (
    IFinancialDataRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_finance_repo import (
    StockFinanceRepositoryImpl,
)
from src.modules.data_engineering.application.commands.get_stock_basic_info import (
    GetStockBasicInfoUseCase,
)
from src.modules.data_engineering.application.queries.get_valuation_dailies_for_ticker import (
    GetValuationDailiesForTickerUseCase,
)
from src.modules.data_engineering.application.queries.get_finance_for_ticker import (
    GetFinanceForTickerUseCase,
)

# Research Infrastructure Adapters
from src.modules.research.infrastructure.adapters.valuation_data_adapter import (
    ValuationDataAdapter,
)
from src.modules.research.infrastructure.valuation_snapshot.snapshot_builder import (
    ValuationSnapshotBuilderImpl,
)
from src.modules.research.infrastructure.adapters.valuation_modeler_agent_adapter import (
    ValuationModelerAgentAdapter,
)
from src.modules.research.infrastructure.adapters.llm_adapter import LLMAdapter
from src.modules.llm_platform.application.services.llm_service import LLMService


router = APIRouter(prefix="/research", tags=["Research"])


# ---------- 依赖注入 ----------
async def get_stock_info_repo(
    db: AsyncSession = Depends(get_db_session),
) -> IStockBasicRepository:
    """获取股票信息仓储。"""
    return StockRepositoryImpl(db)


async def get_market_quote_repo(
    db: AsyncSession = Depends(get_db_session),
) -> IMarketQuoteRepository:
    """获取市场行情仓储。"""
    return StockDailyRepositoryImpl(db)


async def get_financial_repo(
    db: AsyncSession = Depends(get_db_session),
) -> IFinancialDataRepository:
    """获取财务数据仓储。"""
    return StockFinanceRepositoryImpl(db)


async def get_stock_basic_info_use_case(
    info_repo: IStockBasicRepository = Depends(get_stock_info_repo),
    quote_repo: IMarketQuoteRepository = Depends(get_market_quote_repo),
) -> GetStockBasicInfoUseCase:
    return GetStockBasicInfoUseCase(
        stock_repo=info_repo, daily_repo=quote_repo
    )


async def get_valuation_dailies_use_case(
    quote_repo: IMarketQuoteRepository = Depends(get_market_quote_repo),
) -> GetValuationDailiesForTickerUseCase:
    return GetValuationDailiesForTickerUseCase(market_quote_repo=quote_repo)


async def get_finance_use_case(
    finance_repo: IFinancialDataRepository = Depends(get_financial_repo),
) -> GetFinanceForTickerUseCase:
    return GetFinanceForTickerUseCase(financial_repo=finance_repo)


async def get_valuation_data_adapter(
    basic_info_use_case: GetStockBasicInfoUseCase = Depends(
        get_stock_basic_info_use_case
    ),
    valuation_dailies_use_case: GetValuationDailiesForTickerUseCase = Depends(
        get_valuation_dailies_use_case
    ),
    finance_use_case: GetFinanceForTickerUseCase = Depends(get_finance_use_case),
) -> ValuationDataAdapter:
    return ValuationDataAdapter(
        get_stock_basic_info_use_case=basic_info_use_case,
        get_valuation_dailies_use_case=valuation_dailies_use_case,
        get_finance_use_case=finance_use_case,
    )


def get_snapshot_builder() -> ValuationSnapshotBuilderImpl:
    return ValuationSnapshotBuilderImpl()


def get_llm_service() -> LLMService:
    return LLMService()


def get_llm_adapter(service: LLMService = Depends(get_llm_service)) -> LLMAdapter:
    return LLMAdapter(llm_service=service)


def get_modeler_agent_adapter(
    llm_adapter: LLMAdapter = Depends(get_llm_adapter),
) -> ValuationModelerAgentAdapter:
    return ValuationModelerAgentAdapter(llm_port=llm_adapter)


async def get_valuation_modeler_service(
    valuation_data_adapter: ValuationDataAdapter = Depends(get_valuation_data_adapter),
    snapshot_builder: ValuationSnapshotBuilderImpl = Depends(get_snapshot_builder),
    modeler_agent_adapter: ValuationModelerAgentAdapter = Depends(
        get_modeler_agent_adapter
    ),
) -> ValuationModelerService:
    """装配估值建模师服务：获取估值数据 Port、快照构建器、估值建模 Agent Port。"""
    return ValuationModelerService(
        valuation_data_port=valuation_data_adapter,
        snapshot_builder=snapshot_builder,
        modeler_agent_port=modeler_agent_adapter,
    )


# ---------- 响应模型 ----------
class IntrinsicValueRangeResponse(BaseModel):
    """内在价值区间响应。"""

    lower_bound: str = Field(..., description="保守模型推导的价格下界（含推导依据）")
    upper_bound: str = Field(..., description="乐观模型推导的价格上界（含推导依据）")


class ValuationModelApiResponse(BaseModel):
    """估值建模接口响应：解析结果 + input、valuation_indicators、output。"""

    valuation_verdict: Literal["Undervalued (低估)", "Fair (合理)", "Overvalued (高估)"]
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度 0~1")
    estimated_intrinsic_value_range: IntrinsicValueRangeResponse
    key_evidence: list[str] = Field(..., min_length=1, description="证据列表")
    risk_factors: list[str] = Field(..., min_length=1, description="风险列表")
    reasoning_summary: str = Field(..., description="专业精炼总结")
    input: str = Field(..., description="送入大模型的 user prompt")
    valuation_indicators: dict[str, Any] = Field(
        ..., description="估值指标快照（用于填充 prompt）"
    )
    output: str = Field(..., description="大模型原始返回字符串")


# ---------- 接口 ----------
@router.get(
    "/valuation-model",
    response_model=ValuationModelApiResponse,
    summary="对指定股票进行估值建模",
    description='基于基本面数据计算标的的"内在价值"与"安全边际"，剥离市场情绪，仅基于估值模型和财务指标进行判断。响应体含 input、valuation_indicators、output（代码塞入）。',
)
async def run_valuation_model(
    symbol: str = Query(..., description="股票代码，如 000001.SZ"),
    service: ValuationModelerService = Depends(get_valuation_modeler_service),
) -> ValuationModelApiResponse:
    """
    对单个标的运行估值建模；响应体包含解析结果及 input、valuation_indicators、output（由代码填入）。
    """
    try:
        result = await service.run(symbol=symbol.strip())
        return ValuationModelApiResponse(**result)
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except LLMOutputParseError as e:
        logger.warning("估值建模 LLM 解析失败: {}", e.message)
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.exception("估值建模执行异常: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
