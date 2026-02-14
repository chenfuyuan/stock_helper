"""
催化剂侦探搜索维度配置。

定义四个催化维度的搜索配置，遵循聚焦查询规范（核心领域关键词 ≤ 3），
所有维度查询包含 stock_name。
"""
from src.modules.research.domain.dtos.search_dimension_config import SearchDimensionConfig

# 催化剂侦探四维度搜索配置
CATALYST_SEARCH_DIMENSIONS = [
    SearchDimensionConfig(
        topic="公司重大事件与动态",
        query_template="{stock_name} 并购重组 重大公告 {current_year}年",
        count=8,
        freshness="oneWeek",
    ),
    SearchDimensionConfig(
        topic="行业催化与竞争格局",
        query_template="{stock_name} {industry} 竞争格局 技术突破 {current_year}年",
        count=6,
        freshness="oneMonth",
    ),
    SearchDimensionConfig(
        topic="市场情绪与机构动向",
        query_template="{stock_name} 机构评级 分析师 调研 {current_year}年",
        count=8,
        freshness="oneWeek",
    ),
    SearchDimensionConfig(
        topic="财报预期与业绩催化",
        query_template="{stock_name} 业绩预告 财报 盈利预测 {current_year}年",
        count=6,
        freshness="oneMonth",
    ),
]
