"""
Markdown 报告生成器
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.modules.market_insight.domain.model.concept_heat import ConceptHeat
from src.modules.market_insight.domain.model.limit_up_stock import LimitUpStock


class MarkdownReportGenerator:
    """Markdown 报告生成器"""

    def __init__(self, output_dir: str = "reports"):
        self._output_dir = output_dir

    def generate(
        self,
        concept_heats: List[ConceptHeat],
        limit_up_stocks: List[LimitUpStock],
        top_n: int = 10,
    ) -> str:
        """
        生成 Markdown 日报文件
        :param concept_heats: 概念热度列表（已按 avg_pct_chg 降序）
        :param limit_up_stocks: 涨停股列表
        :param top_n: 显示前 N 个强势概念，默认 10
        :return: 生成的报告文件路径
        """
        if not concept_heats:
            raise ValueError("概念热度数据为空，无法生成报告")

        trade_date = concept_heats[0].trade_date
        output_path = self._get_output_path(trade_date)

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 生成报告内容
        content = self._build_report_content(
            trade_date, concept_heats, limit_up_stocks, top_n
        )

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def _get_output_path(self, trade_date) -> str:
        """获取输出文件路径"""
        filename = f"{trade_date.strftime('%Y-%m-%d')}-market-insight.md"
        return os.path.join(self._output_dir, filename)

    def _build_report_content(
        self,
        trade_date,
        concept_heats: List[ConceptHeat],
        limit_up_stocks: List[LimitUpStock],
        top_n: int,
    ) -> str:
        """构建报告内容"""
        lines = []

        # 标题
        lines.append(f"# 每日市场洞察 - {trade_date.strftime('%Y-%m-%d')}")
        lines.append("")

        # Top N 强势概念
        lines.append(f"## Top {top_n} 强势概念")
        lines.append("")
        lines.append("| 排名 | 概念名称 | 涨跌幅(%) | 涨停家数 | 成交额(亿) |")
        lines.append("|------|---------|----------|---------|-----------|")

        top_concepts = concept_heats[:top_n]
        for idx, heat in enumerate(top_concepts, 1):
            amount_yi = heat.total_amount / 100000000
            lines.append(
                f"| {idx} | {heat.concept_name} | {heat.avg_pct_chg:.2f} | "
                f"{heat.limit_up_count} | {amount_yi:.2f} |"
            )

        lines.append("")

        # 今日涨停天梯
        lines.append("## 今日涨停天梯")
        lines.append("")

        if not limit_up_stocks:
            lines.append("今日无涨停。")
        else:
            # 按概念分组
            concept_groups = self._group_limit_up_by_concept(
                limit_up_stocks, concept_heats[:top_n]
            )

            for concept_name, stocks in concept_groups.items():
                lines.append(f"### {concept_name}")
                lines.append("")
                for stock in stocks:
                    lines.append(
                        f"- **{stock.stock_name}** ({stock.third_code}) "
                        f"+{stock.pct_chg:.2f}%"
                    )
                lines.append("")

        # 市场概览
        lines.append("## 市场概览")
        lines.append("")
        lines.append(f"- **涨停总数**: {len(limit_up_stocks)} 只")
        lines.append(f"- **概念板块总数**: {len(concept_heats)} 个")
        lines.append("")

        # 数据更新时间
        lines.append("---")
        lines.append("")
        now = datetime.now()
        lines.append(f"*报告生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")

        return "\n".join(lines)

    def _group_limit_up_by_concept(
        self,
        limit_up_stocks: List[LimitUpStock],
        top_concepts: List[ConceptHeat],
    ) -> dict:
        """按概念分组涨停股"""
        # 提取 top 概念的代码集合
        top_concept_codes = {c.concept_code for c in top_concepts}

        # 按概念分组
        groups = {}
        for stock in limit_up_stocks:
            # 找出该股票属于哪些 top 概念
            matched_concepts = [
                (code, name)
                for code, name in zip(stock.concept_codes, stock.concept_names)
                if code in top_concept_codes
            ]

            if matched_concepts:
                # 如果属于多个 top 概念，使用第一个
                concept_name = matched_concepts[0][1]
                if concept_name not in groups:
                    groups[concept_name] = []
                groups[concept_name].append(stock)

        # 按概念热度排序
        concept_order = {c.concept_name: idx for idx, c in enumerate(top_concepts)}
        sorted_groups = {
            k: v
            for k, v in sorted(
                groups.items(), key=lambda x: concept_order.get(x[0], 999)
            )
        }

        return sorted_groups

    def generate_extended_report(
        self,
        concept_heats: List[ConceptHeat],
        limit_up_stocks: List[LimitUpStock],
        sentiment_metrics: Optional[Dict[str, Any]] = None,
        capital_flow_analysis: Optional[Dict[str, Any]] = None,
        top_n: int = 10,
    ) -> str:
        """
        生成扩展 Markdown 日报文件（包含市场情绪和资金动向）
        :param concept_heats: 概念热度列表（已按 avg_pct_chg 降序）
        :param limit_up_stocks: 涨停股列表
        :param sentiment_metrics: 市场情绪指标
        :param capital_flow_analysis: 资金流向分析
        :param top_n: 显示前 N 个强势概念，默认 10
        :return: 生成的报告文件路径
        """
        if not concept_heats and not sentiment_metrics and not capital_flow_analysis:
            raise ValueError("无数据可生成报告")

        trade_date = concept_heats[0].trade_date if concept_heats else datetime.now().date()
        output_path = self._get_output_path(trade_date)

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 生成报告内容
        content = self._build_extended_report_content(
            trade_date, concept_heats, limit_up_stocks, sentiment_metrics, capital_flow_analysis, top_n
        )

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def _build_extended_report_content(
        self,
        trade_date,
        concept_heats: List[ConceptHeat],
        limit_up_stocks: List[LimitUpStock],
        sentiment_metrics: Optional[Dict[str, Any]],
        capital_flow_analysis: Optional[Dict[str, Any]],
        top_n: int,
    ) -> str:
        """构建扩展报告内容"""
        lines = []

        # 标题
        lines.append(f"# 每日市场洞察 - {trade_date.strftime('%Y-%m-%d')}")
        lines.append("")

        # 市场情绪章节
        lines.append("## 市场情绪")
        lines.append("")
        if sentiment_metrics:
            lines.append(self._build_sentiment_section(sentiment_metrics))
        else:
            lines.append("市场情绪数据暂不可用。")
        lines.append("")

        # 资金动向章节
        lines.append("## 资金动向")
        lines.append("")
        if capital_flow_analysis:
            lines.append(self._build_capital_flow_section(capital_flow_analysis))
        else:
            lines.append("资金流向数据暂不可用。")
        lines.append("")

        # Top N 强势概念
        if concept_heats:
            lines.append(f"## Top {top_n} 强势概念")
            lines.append("")
            lines.append("| 排名 | 概念名称 | 涨跌幅(%) | 涨停家数 | 成交额(亿) |")
            lines.append("|------|---------|----------|---------|-----------|")

            top_concepts = concept_heats[:top_n]
            for idx, heat in enumerate(top_concepts, 1):
                amount_yi = heat.total_amount / 100000000
                lines.append(
                    f"| {idx} | {heat.concept_name} | {heat.avg_pct_chg:.2f} | "
                    f"{heat.limit_up_count} | {amount_yi:.2f} |"
                )

            lines.append("")

            # 今日涨停天梯
            lines.append("## 今日涨停天梯")
            lines.append("")

            if not limit_up_stocks:
                lines.append("今日无涨停。")
            else:
                # 按概念分组
                concept_groups = self._group_limit_up_by_concept(
                    limit_up_stocks, top_concepts
                )

                for concept_name, stocks in concept_groups.items():
                    lines.append(f"### {concept_name}")
                    lines.append("")
                    for stock in stocks:
                        lines.append(
                            f"- **{stock.stock_name}** ({stock.third_code}) "
                            f"+{stock.pct_chg:.2f}%"
                        )
                    lines.append("")

        # 市场概览
        lines.append("## 市场概览")
        lines.append("")
        lines.append(f"- **涨停总数**: {len(limit_up_stocks)} 只")
        if concept_heats:
            lines.append(f"- **概念板块总数**: {len(concept_heats)} 个")
        lines.append("")

        # 数据更新时间
        lines.append("---")
        lines.append("")
        now = datetime.now()
        lines.append(f"*报告生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")

        return "\n".join(lines)

    def _build_sentiment_section(self, sentiment_metrics: Dict[str, Any]) -> str:
        """构建市场情绪章节"""
        lines = []

        # 连板梯队
        ladder = sentiment_metrics.get("consecutive_board_ladder", {})
        if ladder:
            lines.append("### 连板梯队")
            lines.append("")
            lines.append(f"- **最高连板**: {ladder.get('max_height', 0)} 板")
            lines.append(f"- **涨停总数**: {ladder.get('total_limit_up_count', 0)} 只")
            
            tiers = ladder.get("tiers", [])
            if tiers:
                lines.append("")
                lines.append("| 连板数 | 股票数量 | 代表股票 |")
                lines.append("|--------|----------|----------|")
                for tier in tiers:
                    stocks = tier.get("stocks", [])
                    sample_stocks = ", ".join(stocks[:3])  # 显示前3只
                    if len(stocks) > 3:
                        sample_stocks += f" 等{len(stocks)}只"
                    lines.append(
                        f"| {tier.get('board_count', 0)}板 | {len(stocks)} | {sample_stocks} |"
                    )
            lines.append("")

        # 昨日涨停表现
        performance = sentiment_metrics.get("previous_limit_up_performance", {})
        if performance:
            lines.append("### 昨日涨停表现")
            lines.append("")
            lines.append(f"- **昨日涨停总数**: {performance.get('total_count', 0)} 只")
            lines.append(f"- **今日上涨**: {performance.get('up_count', 0)} 只")
            lines.append(f"- **今日下跌**: {performance.get('down_count', 0)} 只")
            lines.append(f"- **赚钱效应**: {performance.get('profit_rate', 0):.1f}%")
            lines.append(f"- **平均涨跌幅**: {performance.get('avg_pct_chg', 0):.2f}%")
            lines.append("")

        # 炸板分析
        broken = sentiment_metrics.get("broken_board_analysis", {})
        if broken:
            lines.append("### 炸板分析")
            lines.append("")
            lines.append(f"- **炸板家数**: {broken.get('broken_count', 0)} 只")
            lines.append(f"- **曾触板总数**: {broken.get('total_attempted', 0)} 只")
            lines.append(f"- **炸板率**: {broken.get('broken_rate', 0):.1f}%")
            lines.append("")

        return "\n".join(lines)

    def _build_capital_flow_section(self, capital_flow_analysis: Dict[str, Any]) -> str:
        """构建资金动向章节"""
        lines = []

        # 龙虎榜分析
        dragon_tiger = capital_flow_analysis.get("dragon_tiger_analysis", {})
        if dragon_tiger:
            lines.append("### 龙虎榜汇总")
            lines.append("")
            lines.append(f"- **上榜个股数**: {dragon_tiger.get('total_count', 0)} 只")
            lines.append(f"- **合计净买入**: {dragon_tiger.get('total_net_buy', 0)/100000000:.2f} 亿元")
            
            institutional = dragon_tiger.get("institutional_activity", [])
            if institutional:
                lines.append(f"- **机构参与**: {len(institutional)} 只")
            lines.append("")

        # 板块资金流向
        sector_flow = capital_flow_analysis.get("sector_capital_flow_analysis", {})
        if sector_flow:
            lines.append("### 板块资金流向")
            lines.append("")
            lines.append(f"- **参与板块数**: {sector_flow.get('total_sectors', 0)} 个")
            lines.append(f"- **板块平均涨跌幅**: {sector_flow.get('avg_pct_chg', 0):.2f}%")
            
            top_inflows = sector_flow.get("top_inflow_sectors", [])
            if top_inflows:
                lines.append("")
                lines.append("#### 净流入前5")
                lines.append("| 板块名称 | 净流入(万) | 涨跌幅(%) |")
                lines.append("|---------|-----------|----------|")
                for sector in top_inflows[:5]:
                    lines.append(
                        f"| {sector.get('sector_name', '')} | {sector.get('net_amount', 0):.0f} | {sector.get('pct_chg', 0):.2f} |"
                    )
            lines.append("")

        return "\n".join(lines)
