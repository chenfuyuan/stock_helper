"""
宏观情报员搜索维度配置。

定义四个宏观维度的搜索配置，遵循聚焦查询规范（核心领域关键词 ≤ 3）。
"""
from src.modules.research.domain.dtos.search_dimension_config import SearchDimensionConfig

# 宏观情报员四维度搜索配置
MACRO_SEARCH_DIMENSIONS = [
    SearchDimensionConfig(
        topic="货币与流动性",
        query_template="{current_year}年 中国 央行 货币政策",
        count=6,
        freshness="oneMonth",
    ),
    SearchDimensionConfig(
        topic="产业政策",
        query_template="{industry} 产业政策 监管政策 {current_year}年",
        count=6,
        freshness="oneMonth",
    ),
    SearchDimensionConfig(
        topic="宏观经济",
        query_template="中国 宏观经济 GDP CPI PMI {current_year}年",
        count=6,
        freshness="oneMonth",
    ),
    SearchDimensionConfig(
        topic="行业景气",
        query_template="{industry} 行业景气 发展趋势 市场前景 {current_year}年",
        count=6,
        freshness="oneMonth",
    ),
]
