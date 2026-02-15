"""
每日复盘 CLI 入口
用于触发每日复盘报告生成
"""

import argparse
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.market_insight.container import MarketInsightContainer
from src.shared.infrastructure.db.session import async_session_factory

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def generate_daily_review(trade_date: date, output_dir: str = "reports"):
    """
    生成每日复盘报告
    :param trade_date: 交易日期
    :param output_dir: 报告输出目录
    """
    async with async_session_factory() as session:
        container = MarketInsightContainer(session, report_output_dir=output_dir)
        cmd = container.get_generate_daily_report_cmd()

        logger.info(f"开始生成每日复盘报告: {trade_date}")

        result = await cmd.execute(trade_date)

        logger.info(
            f"每日复盘报告生成完成:\n"
            f"  交易日期: {result.trade_date}\n"
            f"  概念数量: {result.concept_count}\n"
            f"  涨停数量: {result.limit_up_count}\n"
            f"  报告路径: {result.report_path}\n"
            f"  耗时: {result.elapsed_seconds:.2f}秒"
        )


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(description="Market Insight 每日复盘报告生成")
    parser.add_argument(
        "--date",
        type=str,
        help="交易日期（格式: YYYY-MM-DD），默认为今天",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="报告输出目录",
        default="reports",
    )

    args = parser.parse_args()

    # 解析日期
    if args.date:
        try:
            trade_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"无效的日期格式: {args.date}，请使用 YYYY-MM-DD 格式")
            return
    else:
        trade_date = date.today()

    # 执行任务
    asyncio.run(generate_daily_review(trade_date, args.output_dir))


if __name__ == "__main__":
    main()
