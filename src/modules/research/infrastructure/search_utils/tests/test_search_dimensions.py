"""
搜索维度配置合规测试。

断言每个 SearchDimensionConfig 的查询模板核心关键词 ≤ 3、count 在 4-10 范围、freshness 为合法值。
"""
import pytest

from src.modules.research.infrastructure.search_utils.macro_search_dimensions import MACRO_SEARCH_DIMENSIONS
from src.modules.research.infrastructure.search_utils.catalyst_search_dimensions import CATALYST_SEARCH_DIMENSIONS


def count_core_keywords(query_template: str) -> int:
    """
    计算查询模板中的核心领域关键词数量。
    
    不计占位符（{stock_name}、{industry}、{current_year}）。
    """
    # 移除占位符
    cleaned = query_template.replace("{stock_name}", "").replace("{industry}", "").replace("{current_year}", "")
    
    # 按空格分割，过滤空字符串和纯数字年份
    tokens = [token for token in cleaned.split() if token and not token.isdigit() and token != "年"]
    
    return len(tokens)


class TestMacroSearchDimensions:
    def test_macro_dimensions_compliance(self):
        """测试宏观情报员搜索维度配置合规性"""
        for config in MACRO_SEARCH_DIMENSIONS:
            # 检查 count 范围
            assert 4 <= config.count <= 10, f"宏观维度 {config.topic} 的 count {config.count} 不在 4-10 范围内"
            
            # 检查 freshness 合法值
            valid_freshness = ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]
            assert config.freshness in valid_freshness, f"宏观维度 {config.topic} 的 freshness {config.freshness} 不是合法值"
            
            # 检查核心关键词数量
            core_keywords = count_core_keywords(config.query_template)
            assert core_keywords <= 3, f"宏观维度 {config.topic} 的查询模板核心关键词数量 {core_keywords} 超过 3 个"
            
            # 检查查询模板包含占位符
            assert "{current_year}" in config.query_template, f"宏观维度 {config.topic} 的查询模板缺少 {current_year} 占位符"

    def test_macro_dimensions_unique_topics(self):
        """测试宏观维度主题唯一性"""
        topics = [config.topic for config in MACRO_SEARCH_DIMENSIONS]
        assert len(topics) == len(set(topics)), "宏观维度主题存在重复"


class TestCatalystSearchDimensions:
    def test_catalyst_dimensions_compliance(self):
        """测试催化剂侦探搜索维度配置合规性"""
        for config in CATALYST_SEARCH_DIMENSIONS:
            # 检查 count 范围
            assert 4 <= config.count <= 10, f"催化剂维度 {config.topic} 的 count {config.count} 不在 4-10 范围内"
            
            # 检查 freshness 合法值
            valid_freshness = ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]
            assert config.freshness in valid_freshness, f"催化剂维度 {config.topic} 的 freshness {config.freshness} 不是合法值"
            
            # 检查核心关键词数量
            core_keywords = count_core_keywords(config.query_template)
            assert core_keywords <= 3, f"催化剂维度 {config.topic} 的查询模板核心关键词数量 {core_keywords} 超过 3 个"
            
            # 检查查询模板包含占位符
            assert "{stock_name}" in config.query_template, f"催化剂维度 {config.topic} 的查询模板缺少 {stock_name} 占位符"
            assert "{current_year}" in config.query_template, f"催化剂维度 {config.topic} 的查询模板缺少 {current_year} 占位符"

    def test_catalyst_dimensions_unique_topics(self):
        """测试催化剂维度主题唯一性"""
        topics = [config.topic for config in CATALYST_SEARCH_DIMENSIONS]
        assert len(topics) == len(set(topics)), "催化剂维度主题存在重复"

    def test_catalyst_dimensions_stock_name_in_all_queries(self):
        """测试催化剂所有维度查询都包含 stock_name"""
        for config in CATALYST_SEARCH_DIMENSIONS:
            assert "{stock_name}" in config.query_template, f"催化剂维度 {config.topic} 的查询模板必须包含 {stock_name}"
