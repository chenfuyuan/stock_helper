"""
Market Insight 模块 DI 容器
组装全部依赖：Adapters、Repositories、Services、Commands、Queries
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.container import DataEngineeringContainer
from src.modules.market_insight.application.commands.generate_daily_report_cmd import (
    GenerateDailyReportCmd,
)
from src.modules.market_insight.application.queries.get_concept_heat_query import (
    GetConceptHeatQuery,
)
from src.modules.market_insight.application.queries.get_capital_flow_analysis import (
    GetCapitalFlowAnalysisQuery,
)
from src.modules.market_insight.application.queries.get_limit_up_query import (
    GetLimitUpQuery,
)
from src.modules.market_insight.application.queries.get_sentiment_metrics import (
    GetSentimentMetricsQuery,
)
from src.modules.market_insight.domain.services.capital_flow_analyzer import (
    CapitalFlowAnalyzer,
)
from src.modules.market_insight.domain.services.concept_heat_calculator import (
    ConceptHeatCalculator,
)
from src.modules.market_insight.domain.services.limit_up_scanner import LimitUpScanner
from src.modules.market_insight.domain.services.sentiment_analyzer import SentimentAnalyzer
from src.modules.market_insight.infrastructure.adapters.de_capital_flow_data_adapter import (
    DeCapitalFlowDataAdapter,
)
from src.modules.market_insight.infrastructure.adapters.de_concept_data_adapter import (
    DeConceptDataAdapter,
)
from src.modules.market_insight.infrastructure.adapters.de_market_data_adapter import (
    DeMarketDataAdapter,
)
from src.modules.market_insight.infrastructure.adapters.de_sentiment_data_adapter import (
    DeSentimentDataAdapter,
)
from src.modules.market_insight.infrastructure.persistence.repositories.pg_concept_heat_repo import (
    PgConceptHeatRepository,
)
from src.modules.market_insight.infrastructure.persistence.repositories.pg_limit_up_repo import (
    PgLimitUpRepository,
)
from src.modules.market_insight.infrastructure.report.markdown_report_generator import (
    MarkdownReportGenerator,
)


class MarketInsightContainer:
    """Market Insight 模块依赖注入容器"""

    def __init__(self, session: AsyncSession, report_output_dir: str = "reports"):
        self._session = session
        self._report_output_dir = report_output_dir

        # 初始化 data_engineering 容器
        self._de_container = DataEngineeringContainer(session)

        # 初始化 Adapters
        self._concept_data_port = DeConceptDataAdapter(self._de_container)
        self._market_data_port = DeMarketDataAdapter(self._de_container)
        self._sentiment_data_port = DeSentimentDataAdapter(
            limit_up_pool_use_case=self._de_container.get_limit_up_pool_by_date_use_case(),
            broken_board_use_case=self._de_container.get_broken_board_by_date_use_case(),
            previous_limit_up_use_case=self._de_container.get_previous_limit_up_by_date_use_case(),
        )
        self._capital_flow_data_port = DeCapitalFlowDataAdapter(
            dragon_tiger_use_case=self._de_container.get_dragon_tiger_by_date_use_case(),
            sector_capital_flow_use_case=self._de_container.get_sector_capital_flow_by_date_use_case(),
        )

        # 初始化 Repositories
        self._concept_heat_repo = PgConceptHeatRepository(session)
        self._limit_up_repo = PgLimitUpRepository(session)

        # 初始化 Domain Services
        self._concept_heat_calculator = ConceptHeatCalculator()
        self._limit_up_scanner = LimitUpScanner()
        self._sentiment_analyzer = SentimentAnalyzer()
        self._capital_flow_analyzer = CapitalFlowAnalyzer()

        # 初始化 Report Generator
        self._report_generator = MarkdownReportGenerator(
            output_dir=self._report_output_dir
        )

    def get_concept_heat_calculator(self) -> ConceptHeatCalculator:
        """获取概念热度计算器"""
        return self._concept_heat_calculator

    def get_limit_up_scanner(self) -> LimitUpScanner:
        """获取涨停扫描器"""
        return self._limit_up_scanner

    def get_concept_heat_repo(self) -> PgConceptHeatRepository:
        """获取概念热度 Repository"""
        return self._concept_heat_repo

    def get_limit_up_repo(self) -> PgLimitUpRepository:
        """获取涨停股 Repository"""
        return self._limit_up_repo

    def get_generate_daily_report_cmd(self) -> GenerateDailyReportCmd:
        """获取生成每日复盘报告命令"""
        return GenerateDailyReportCmd(
            concept_data_port=self._concept_data_port,
            market_data_port=self._market_data_port,
            sentiment_data_port=self._sentiment_data_port,
            capital_flow_data_port=self._capital_flow_data_port,
            concept_heat_repo=self._concept_heat_repo,
            limit_up_repo=self._limit_up_repo,
            concept_heat_calculator=self._concept_heat_calculator,
            limit_up_scanner=self._limit_up_scanner,
            sentiment_analyzer=self._sentiment_analyzer,
            capital_flow_analyzer=self._capital_flow_analyzer,
            report_generator=self._report_generator,
        )

    def get_concept_heat_query(self) -> GetConceptHeatQuery:
        """获取概念热度查询用例"""
        return GetConceptHeatQuery(concept_heat_repo=self._concept_heat_repo)

    def get_limit_up_query(self) -> GetLimitUpQuery:
        """获取涨停股查询用例"""
        return GetLimitUpQuery(limit_up_repo=self._limit_up_repo)

    def get_sentiment_metrics_query(self) -> GetSentimentMetricsQuery:
        """获取市场情绪指标查询用例"""
        return GetSentimentMetricsQuery(
            sentiment_data_port=self._sentiment_data_port,
            sentiment_analyzer=self._sentiment_analyzer,
        )

    def get_capital_flow_analysis_query(self) -> GetCapitalFlowAnalysisQuery:
        """获取资金流向分析查询用例"""
        return GetCapitalFlowAnalysisQuery(
            capital_flow_data_port=self._capital_flow_data_port,
            capital_flow_analyzer=self._capital_flow_analyzer,
        )
