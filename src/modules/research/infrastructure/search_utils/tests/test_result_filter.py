"""
SearchResultFilter 单元测试。

覆盖去重、去空标题、去无内容、有效条目保留、排序（有日期降序 + 无日期末尾）。
"""
import pytest
from src.modules.llm_platform.domain.web_search_dtos import WebSearchResultItem
from src.modules.research.infrastructure.search_utils.result_filter import SearchResultFilter


class TestSearchResultFilter:
    def setup_method(self):
        self.filter = SearchResultFilter()

    def test_url_deduplication(self):
        """测试 URL 去重：同一 URL 仅保留首次出现的条目"""
        items = [
            WebSearchResultItem(
                title="标题1",
                url="https://example.com/article1",
                snippet="摘要1",
                summary="AI摘要1",
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="标题2",
                url="https://example.com/article1",  # 同一 URL
                snippet="摘要2",
                summary="AI摘要2",
                site_name="站点2",
                published_date="2024-01-02",
            ),
            WebSearchResultItem(
                title="标题3",
                url="https://example.com/article3",
                snippet="摘要3",
                summary="AI摘要3",
                site_name="站点3",
                published_date="2024-01-03",
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 2
        assert result[0].title == "标题1"  # 保留首次出现的条目
        assert result[1].title == "标题3"

    def test_remove_empty_title(self):
        """测试去空标题：title 为空或全空白的条目被剔除"""
        items = [
            WebSearchResultItem(
                title="有效标题",
                url="https://example.com/article1",
                snippet="摘要1",
                summary="AI摘要1",
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="",  # 空标题
                url="https://example.com/article2",
                snippet="摘要2",
                summary="AI摘要2",
                site_name="站点2",
                published_date="2024-01-02",
            ),
            WebSearchResultItem(
                title="   ",  # 全空白标题
                url="https://example.com/article3",
                snippet="摘要3",
                summary="AI摘要3",
                site_name="站点3",
                published_date="2024-01-03",
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 1
        assert result[0].title == "有效标题"

    def test_remove_no_content(self):
        """测试去无内容：summary 和 snippet 均为空的条目被剔除"""
        items = [
            WebSearchResultItem(
                title="有效条目",
                url="https://example.com/article1",
                snippet="有摘要",
                summary="有AI摘要",
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="无内容条目1",
                url="https://example.com/article2",
                snippet="",  # 空 snippet
                summary="",  # 空 summary
                site_name="站点2",
                published_date="2024-01-02",
            ),
            WebSearchResultItem(
                title="无内容条目2",
                url="https://example.com/article3",
                snippet="   ",  # 全空白 snippet
                summary="   ",  # 全空白 summary
                site_name="站点3",
                published_date="2024-01-03",
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 1
        assert result[0].title == "有效条目"

    def test_keep_valid_items(self):
        """测试有效条目保留：有 title 且至少有 summary 或 snippet 的条目被保留"""
        items = [
            WebSearchResultItem(
                title="有摘要无AI摘要",
                url="https://example.com/article1",
                snippet="有摘要",
                summary="",  # AI摘要为空
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="有AI摘要无摘要",
                url="https://example.com/article2",
                snippet="",  # 摘要为空
                summary="有AI摘要",
                site_name="站点2",
                published_date="2024-01-02",
            ),
            WebSearchResultItem(
                title="两者都有",
                url="https://example.com/article3",
                snippet="有摘要",
                summary="有AI摘要",
                site_name="站点3",
                published_date="2024-01-03",
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 3
        titles = [item.title for item in result]
        assert "有摘要无AI摘要" in titles
        assert "有AI摘要无摘要" in titles
        assert "两者都有" in titles

    def test_sort_by_published_date_descending(self):
        """测试按 published_date 降序排序：最近的在前"""
        items = [
            WebSearchResultItem(
                title="最早",
                url="https://example.com/article1",
                snippet="摘要1",
                summary="AI摘要1",
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="最晚",
                url="https://example.com/article2",
                snippet="摘要2",
                summary="AI摘要2",
                site_name="站点2",
                published_date="2024-01-03",
            ),
            WebSearchResultItem(
                title="中间",
                url="https://example.com/article3",
                snippet="摘要3",
                summary="AI摘要3",
                site_name="站点3",
                published_date="2024-01-02",
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 3
        assert result[0].title == "最晚"  # 2024-01-03
        assert result[1].title == "中间"  # 2024-01-02
        assert result[2].title == "最早"  # 2024-01-01

    def test_no_date_items_at_end(self):
        """测试无日期的条目排在末尾"""
        items = [
            WebSearchResultItem(
                title="有日期1",
                url="https://example.com/article1",
                snippet="摘要1",
                summary="AI摘要1",
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="无日期1",
                url="https://example.com/article2",
                snippet="摘要2",
                summary="AI摘要2",
                site_name="站点2",
                published_date=None,
            ),
            WebSearchResultItem(
                title="有日期2",
                url="https://example.com/article3",
                snippet="摘要3",
                summary="AI摘要3",
                site_name="站点3",
                published_date="2024-01-02",
            ),
            WebSearchResultItem(
                title="无日期2",
                url="https://example.com/article4",
                snippet="摘要4",
                summary="AI摘要4",
                site_name="站点4",
                published_date=None,
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 4
        assert result[0].title == "有日期2"  # 2024-01-02
        assert result[1].title == "有日期1"  # 2024-01-01
        # 无日期的条目排在末尾，保持原顺序
        assert result[2].title == "无日期1"
        assert result[3].title == "无日期2"

    def test_empty_input(self):
        """测试空输入"""
        result = self.filter.filter_and_sort([])
        assert result == []

    def test_url_normalization(self):
        """测试 URL 标准化：去除 fragment"""
        items = [
            WebSearchResultItem(
                title="标题1",
                url="https://example.com/article1",
                snippet="摘要1",
                summary="AI摘要1",
                site_name="站点1",
                published_date="2024-01-01",
            ),
            WebSearchResultItem(
                title="标题2",
                url="https://example.com/article1#section",  # 同一 URL，带 fragment
                snippet="摘要2",
                summary="AI摘要2",
                site_name="站点2",
                published_date="2024-01-02",
            ),
        ]

        result = self.filter.filter_and_sort(items)

        assert len(result) == 1
        assert result[0].title == "标题1"  # 保留首次出现的条目
