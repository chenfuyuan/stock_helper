"""
生成每日复盘报告命令
编排完整流程：获取数据 → 构建索引 → 计算热度 → 扫描涨停 → 持久化 → 生成报告
"""

import logging
import time
from datetime import date
from typing import Dict, List

from src.modules.market_insight.application.dtos.market_insight_dtos import (
    DailyReportResult,
)
from src.modules.market_insight.domain.dtos.insight_dtos import ConceptInfoDTO
from src.modules.market_insight.domain.ports.concept_data_port import IConceptDataPort
from src.modules.market_insight.domain.ports.market_data_port import IMarketDataPort
from src.modules.market_insight.domain.ports.repositories.concept_heat_repo import (
    IConceptHeatRepository,
)
from src.modules.market_insight.domain.ports.repositories.limit_up_repo import (
    ILimitUpRepository,
)
from src.modules.market_insight.domain.services.concept_heat_calculator import (
    ConceptHeatCalculator,
)
from src.modules.market_insight.domain.services.limit_up_scanner import LimitUpScanner
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
        concept_heat_repo: IConceptHeatRepository,
        limit_up_repo: ILimitUpRepository,
        concept_heat_calculator: ConceptHeatCalculator,
        limit_up_scanner: LimitUpScanner,
        report_generator: MarkdownReportGenerator,
    ):
        self._concept_data_port = concept_data_port
        self._market_data_port = market_data_port
        self._concept_heat_repo = concept_heat_repo
        self._limit_up_repo = limit_up_repo
        self._concept_heat_calculator = concept_heat_calculator
        self._limit_up_scanner = limit_up_scanner
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

        # 8. 生成 Markdown 报告
        report_path = ""
        if concept_heats:
            # 按 avg_pct_chg 降序排序
            concept_heats_sorted = sorted(
                concept_heats, key=lambda x: x.avg_pct_chg, reverse=True
            )
            report_path = self._report_generator.generate(
                concept_heats_sorted, limit_up_stocks, top_n=10
            )
            logger.info(f"生成 Markdown 报告: {report_path}")

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
        )
