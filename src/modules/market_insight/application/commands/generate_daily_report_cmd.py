"""
生成每日复盘报告命令
编排完整流程：获取数据 → 构建索引 → 计算热度 → 扫描涨停 → 持久化 → 生成报告
"""

import logging
import time
from datetime import date
from typing import Dict, List

from src.modules.market_insight.application.dtos.capital_flow_analysis_dtos import (
    CapitalFlowAnalysisDTO,
)
from src.modules.market_insight.application.dtos.market_insight_dtos import (
    DailyReportResult,
)
from src.modules.market_insight.application.dtos.sentiment_metrics_dtos import (
    SentimentMetricsDTO,
)
from src.modules.market_insight.domain.dtos.insight_dtos import ConceptInfoDTO
from src.modules.market_insight.domain.ports.capital_flow_data_port import ICapitalFlowDataPort
from src.modules.market_insight.domain.ports.concept_data_port import IConceptDataPort
from src.modules.market_insight.domain.ports.market_data_port import IMarketDataPort
from src.modules.market_insight.domain.ports.sentiment_data_port import ISentimentDataPort
from src.modules.market_insight.domain.ports.repositories.concept_heat_repo import (
    IConceptHeatRepository,
)
from src.modules.market_insight.domain.ports.repositories.limit_up_repo import (
    ILimitUpRepository,
)
from src.modules.market_insight.domain.services.concept_heat_calculator import (
    ConceptHeatCalculator,
)
from src.modules.market_insight.domain.services.capital_flow_analyzer import (
    CapitalFlowAnalyzer,
)
from src.modules.market_insight.domain.services.limit_up_scanner import LimitUpScanner
from src.modules.market_insight.domain.services.sentiment_analyzer import SentimentAnalyzer
from src.modules.market_insight.infrastructure.report.markdown_report_generator import (
    MarkdownReportGenerator,
)

logger = logging.getLogger(__name__)


class GenerateDailyReportCmd:
    """生成每日复盘报告命令"""

    def __init__(
        self,
        concept_data_port: IConceptDataPort,
        market_data_port: IMarketDataPort,
        sentiment_data_port: ISentimentDataPort,
        capital_flow_data_port: ICapitalFlowDataPort,
        concept_heat_repo: IConceptHeatRepository,
        limit_up_repo: ILimitUpRepository,
        concept_heat_calculator: ConceptHeatCalculator,
        limit_up_scanner: LimitUpScanner,
        sentiment_analyzer: SentimentAnalyzer,
        capital_flow_analyzer: CapitalFlowAnalyzer,
        report_generator: MarkdownReportGenerator,
    ):
        self._concept_data_port = concept_data_port
        self._market_data_port = market_data_port
        self._sentiment_data_port = sentiment_data_port
        self._capital_flow_data_port = capital_flow_data_port
        self._concept_heat_repo = concept_heat_repo
        self._limit_up_repo = limit_up_repo
        self._concept_heat_calculator = concept_heat_calculator
        self._limit_up_scanner = limit_up_scanner
        self._sentiment_analyzer = sentiment_analyzer
        self._capital_flow_analyzer = capital_flow_analyzer
        self._report_generator = report_generator

    async def execute(self, trade_date: date) -> DailyReportResult:
        """
        执行每日复盘报告生成
        :param trade_date: 交易日期
        :return: 执行结果摘要
        """
        start_time = time.time()

        logger.info(f"开始生成每日复盘报告: {trade_date}")

        # 1. 获取全市场日线数据
        daily_bars = await self._market_data_port.get_daily_bars_by_date(trade_date)

        if not daily_bars:
            logger.warning(f"无行情数据: {trade_date}（可能为非交易日）")
            elapsed = time.time() - start_time
            return DailyReportResult(
                trade_date=trade_date,
                concept_count=0,
                limit_up_count=0,
                report_path="",
                elapsed_seconds=elapsed,
                sentiment_metrics=None,
                capital_flow_analysis=None,
            )

        logger.info(f"获取到 {len(daily_bars)} 只股票的日线数据")

        # 2. 获取概念及成分股映射
        concepts = await self._concept_data_port.get_all_concepts_with_stocks()
        logger.info(f"获取到 {len(concepts)} 个概念板块")

        # 3. 构建索引：daily_bars dict 和 concept_stock_map
        daily_bars_dict = {bar.third_code: bar for bar in daily_bars}

        concept_stock_map: Dict[str, List[ConceptInfoDTO]] = {}
        for concept in concepts:
            for stock in concept.stocks:
                if stock.third_code not in concept_stock_map:
                    concept_stock_map[stock.third_code] = []
                concept_stock_map[stock.third_code].append(
                    ConceptInfoDTO(code=concept.code, name=concept.name)
                )

        # 4. 计算板块热度
        concept_heats = self._concept_heat_calculator.calculate(
            concepts, daily_bars_dict
        )
        logger.info(f"计算出 {len(concept_heats)} 个概念的热度")

        # 5. 扫描涨停股
        limit_up_stocks = self._limit_up_scanner.scan(daily_bars, concept_stock_map)
        logger.info(f"识别出 {len(limit_up_stocks)} 只涨停股")

        # 6. 持久化热度数据
        if concept_heats:
            await self._concept_heat_repo.save_all(concept_heats)
            logger.info(f"已持久化 {len(concept_heats)} 条概念热度数据")

        # 7. 持久化涨停数据
        if limit_up_stocks:
            await self._limit_up_repo.save_all(limit_up_stocks)
            logger.info(f"已持久化 {len(limit_up_stocks)} 条涨停股数据")

        # 8. 获取市场情绪数据（异常隔离）
        sentiment_metrics: SentimentMetricsDTO | None = None
        try:
            limit_up_pool = await self._sentiment_data_port.get_limit_up_pool(trade_date)
            broken_board_pool = await self._sentiment_data_port.get_broken_board_pool(trade_date)
            previous_limit_up = await self._sentiment_data_port.get_previous_limit_up(trade_date)

            # 通过领域服务分析
            consecutive_board_ladder = self._sentiment_analyzer.analyze_consecutive_board_ladder(
                limit_up_pool
            )
            previous_limit_up_performance = (
                self._sentiment_analyzer.analyze_previous_limit_up_performance(previous_limit_up)
            )
            broken_board_analysis = self._sentiment_analyzer.analyze_broken_board(
                limit_up_pool, broken_board_pool
            )

            sentiment_metrics = SentimentMetricsDTO(
                trade_date=trade_date,
                consecutive_board_ladder=consecutive_board_ladder,
                previous_limit_up_performance=previous_limit_up_performance,
                broken_board_analysis=broken_board_analysis,
            )
            logger.info("市场情绪分析完成")
        except Exception as e:
            logger.error(f"市场情绪分析失败: {str(e)}")
            sentiment_metrics = None

        # 9. 获取资金流向数据（异常隔离）
        capital_flow_analysis: CapitalFlowAnalysisDTO | None = None
        try:
            dragon_tiger = await self._capital_flow_data_port.get_dragon_tiger(trade_date)
            sector_capital_flow = await self._capital_flow_data_port.get_sector_capital_flow(trade_date)

            # 通过领域服务分析
            dragon_tiger_analysis = self._capital_flow_analyzer.analyze_dragon_tiger(dragon_tiger)
            sector_capital_flow_analysis = self._capital_flow_analyzer.analyze_sector_capital_flow(
                sector_capital_flow
            )

            capital_flow_analysis = CapitalFlowAnalysisDTO(
                trade_date=trade_date,
                dragon_tiger_analysis=dragon_tiger_analysis,
                sector_capital_flow_analysis=sector_capital_flow_analysis,
            )
            logger.info("资金流向分析完成")
        except Exception as e:
            logger.error(f"资金流向分析失败: {str(e)}")
            capital_flow_analysis = None

        # 10. 生成扩展 Markdown 报告
        report_path = ""
        if concept_heats or sentiment_metrics or capital_flow_analysis:
            # 按 avg_pct_chg 降序排序
            concept_heats_sorted = sorted(
                concept_heats, key=lambda x: x.avg_pct_chg, reverse=True
            )
            report_path = self._report_generator.generate_extended_report(
                concept_heats_sorted, limit_up_stocks, sentiment_metrics, capital_flow_analysis, top_n=10
            )
            logger.info(f"生成扩展 Markdown 报告: {report_path}")

        # 11. 返回结果
        elapsed = time.time() - start_time
        logger.info(
            f"每日复盘报告生成完成: 概念数={len(concept_heats)}, "
            f"涨停数={len(limit_up_stocks)}, 耗时={elapsed:.2f}秒"
        )

        return DailyReportResult(
            trade_date=trade_date,
            concept_count=len(concept_heats),
            limit_up_count=len(limit_up_stocks),
            report_path=report_path,
            elapsed_seconds=elapsed,
            sentiment_metrics=sentiment_metrics.model_dump() if sentiment_metrics else None,
            capital_flow_analysis=capital_flow_analysis.model_dump() if capital_flow_analysis else None,
        )
