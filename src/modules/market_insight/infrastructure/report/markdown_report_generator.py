"""
Markdown 报告生成器
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List

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
