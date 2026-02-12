"""
Research 模块 Composition Root。

统一封装技术分析师、财务审计员、估值建模师等 Application Service 的组装逻辑，
跨模块依赖通过 DataEngineeringContainer 和 LLMPlatformContainer 获取，不直接依赖其他模块的 Infrastructure。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.research.application.technical_analyst_service import TechnicalAnalystService
from src.modules.research.application.financial_auditor_service import FinancialAuditorService
from src.modules.research.application.valuation_modeler_service import ValuationModelerService
from src.modules.research.infrastructure.adapters.market_quote_adapter import MarketQuoteAdapter
from src.modules.research.infrastructure.adapters.financial_data_adapter import FinancialDataAdapter
from src.modules.research.infrastructure.adapters.valuation_data_adapter import ValuationDataAdapter
from src.modules.research.infrastructure.adapters.llm_adapter import LLMAdapter
from src.modules.research.infrastructure.adapters.technical_analyst_agent_adapter import (
    TechnicalAnalystAgentAdapter,
)
from src.modules.research.infrastructure.adapters.financial_auditor_agent_adapter import (
    FinancialAuditorAgentAdapter,
)
from src.modules.research.infrastructure.adapters.valuation_modeler_agent_adapter import (
    ValuationModelerAgentAdapter,
)
from src.modules.research.infrastructure.indicators.indicator_calculator_adapter import (
    IndicatorCalculatorAdapter,
)
from src.modules.research.infrastructure.financial_snapshot.snapshot_builder import (
    FinancialSnapshotBuilderImpl,
)
from src.modules.research.infrastructure.valuation_snapshot.snapshot_builder import (
    ValuationSnapshotBuilderImpl,
)


class ResearchContainer:
    """Research 模块的依赖组装容器。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._de_container = self._get_de_container()
        self._llm_container = self._get_llm_container()

    def _get_de_container(self):
        """延迟导入避免循环依赖。"""
        from src.modules.data_engineering.container import DataEngineeringContainer
        return DataEngineeringContainer(self._session)

    def _get_llm_container(self):
        """延迟导入避免循环依赖。"""
        from src.modules.llm_platform.container import LLMPlatformContainer
        return LLMPlatformContainer()

    def technical_analyst_service(self) -> TechnicalAnalystService:
        """组装技术分析师服务：日线 Port、指标计算、技术分析 Agent。"""
        market_quote_adapter = MarketQuoteAdapter(
            get_daily_bars_use_case=self._de_container.get_daily_bars_use_case()
        )
        indicator_calculator = IndicatorCalculatorAdapter()
        llm_adapter = LLMAdapter(llm_service=self._llm_container.llm_service())
        analyst_agent = TechnicalAnalystAgentAdapter(llm_port=llm_adapter)
        return TechnicalAnalystService(
            market_quote_port=market_quote_adapter,
            indicator_calculator=indicator_calculator,
            analyst_agent_port=analyst_agent,
        )

    def financial_auditor_service(self) -> FinancialAuditorService:
        """组装财务审计员服务：财务数据 Port、快照构建器、审计 Agent。"""
        financial_data_adapter = FinancialDataAdapter(
            get_finance_use_case=self._de_container.get_finance_use_case()
        )
        snapshot_builder = FinancialSnapshotBuilderImpl()
        llm_adapter = LLMAdapter(llm_service=self._llm_container.llm_service())
        auditor_agent = FinancialAuditorAgentAdapter(llm_port=llm_adapter)
        return FinancialAuditorService(
            financial_data_port=financial_data_adapter,
            snapshot_builder=snapshot_builder,
            auditor_agent_port=auditor_agent,
        )

    def valuation_modeler_service(self) -> ValuationModelerService:
        """组装估值建模师服务：估值数据 Port、快照构建器、估值建模 Agent。"""
        valuation_data_adapter = ValuationDataAdapter(
            get_stock_basic_info_use_case=self._de_container.get_stock_basic_info_use_case(),
            get_valuation_dailies_use_case=self._de_container.get_valuation_dailies_use_case(),
            get_finance_use_case=self._de_container.get_finance_use_case(),
        )
        snapshot_builder = ValuationSnapshotBuilderImpl()
        llm_adapter = LLMAdapter(llm_service=self._llm_container.llm_service())
        modeler_agent = ValuationModelerAgentAdapter(llm_port=llm_adapter)
        return ValuationModelerService(
            valuation_data_port=valuation_data_adapter,
            snapshot_builder=snapshot_builder,
            modeler_agent_port=modeler_agent,
        )
